import json
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)
from typing import cast
from pydantic import BaseModel
import uuid

from schemas.state import AgentState, ContextQueryExchange, ToolCall
from schemas.tool_selection import ToolSelection
from schemas.context_query import AdditionalContextQuery

from utilities.dependency_helper import (
    get_task,
    dependencies_satisfied,
)
from utilities.context_helper import build_task_context
from utilities.tools_helper import (
    get_tool_specs,
    get_tool,
)
from utilities.load_model import load_models

SYSTEM_TEMPLATE = """
You are a context synthesizer.

Given:
1. Current task
2. Dependency outputs
3. Available tools and schemas
4. Additional context from the pervious query, if any, by this context synthesizer.

Determine:
- Which tool should execute the task
- Construct valid tool arguments
- Verify all required inputs exist

Rules:
- Return only valid arguments matching the selected tool schema.
- If required information is missing, set ready=false.
- Do not execute tools.
- Prefer ready=false over guessing.

## Dependency Outputs
{context}

## Available tools and schemas
{tool_specs}

## Additional Context
{previous_queries}
"""


async def context_synthesizer_node(state: AgentState):
    task = get_task(state, state["current_task_id"])

    assert task is not None
    assert dependencies_satisfied(task, state)

    contexts = build_task_context(task, state)

    available_tools = await get_tool_specs()

    llm = load_models("Planner")
    
    RETRY_COUNT = 3

    # Check for any exception here.
    # additional_context is assumed to be a list of dictionary
    #     {
    #       context_used: str
    #       failure_reason: str
    #       query_response: dict
    #       retry_count: int
    #     }
    
    artifacts_key = f'{task.get("id")}_{task["type"]}'
    additional_contexts = state['artifacts'].get(artifacts_key, None)
    if additional_contexts is not None and additional_contexts[-1]["retry_count"] >= RETRY_COUNT:
        return {
                "current_task_id": None, 
                "messages": [
                    AIMessage(
                        content="Maximum retry reached. Needs user help.",
                        additional_kwargs={
                            "node_name": "context_synthesizer",
                            "next_node": "response_synthesizer"
                        }
                    )
                ]
            }
    
    formatted_system_prompt = SYSTEM_TEMPLATE.format(
        context=json.dumps(contexts, indent=2, default=str),
        tool_specs=json.dumps(available_tools, indent=2, default=str),
        previous_queries=json.dumps(additional_contexts)
    )

    validation_error = ""
    response = None

    for _ in range(RETRY_COUNT):

        messages = [
            SystemMessage(content=formatted_system_prompt),
            HumanMessage(
                content=f"""
                    Current task:

                    {json.dumps(task, indent=2)}

                    Previous validation error:
                    {validation_error if validation_error else "None"}

                    Select the best tool and generate valid arguments.
                """
            ),
        ]

        response = cast(ToolSelection, await (
            llm.with_structured_output(ToolSelection)
            .ainvoke(messages)
        ))

        # Not ready => stop immediately
        if not response.ready:
            break

        # Tool must exist
        tool = await get_tool(response.tool_name) # type: ignore

        if tool is None:
            validation_error = (
                f"Tool '{response.tool_name}' does not exist."
            )
            continue

        try:
            # Validate tool arguments against schema
            if (
                hasattr(tool, "args_schema")
                and tool.args_schema
                and isinstance(tool.args_schema, type)
                and issubclass(tool.args_schema, BaseModel)
            ):
                tool.args_schema.model_validate(
                    response.tool_arguments or {}
                )

            # Success
            validation_error = None
            # break

        except Exception as e:
            validation_error = str(e)

        # Final failure after retries
        if validation_error:
            response.ready = False
            response.reasoning = (
                f"{response.reasoning}\n\n"
                f"Schema validation failed after retries:\n"
                f"{validation_error}"
            )
            continue
        tool_call_id = f"manual_{uuid.uuid4().hex[:8]}"
        # Everything fine, now move to tool call Node
        tool_schema = ToolCall(tool_name=response.tool_name, #type: ignore
                                           args=response.tool_arguments,
                                           tool_call_id=tool_call_id)
        
        return {
            "selected_tool_name": tool_schema,
            "messages": [
                    AIMessage(
                        content=f"Tool Call to tool {tool_schema['tool_name']}",
                        additional_kwargs={
                            "node_name": "context_synthesizer",
                            "next_node": "tool_call"
                        },
                        tool_calls=[{
                            "name": tool_schema['tool_name'],
                            "args": tool_schema['args'],
                            "id": tool_call_id
                        }]
                    )
                ]
        }
        
    
    # Failed to select tool with proper validation
    # Get more context needed
    artifacts = dict(state["artifacts"])

    if artifacts_key not in artifacts:
        artifacts[artifacts_key] = [] #This is must to be a list else logic in upper part will break
    
    ## Ask the LLM to create query
    query_response = await (
    llm.with_structured_output(
        AdditionalContextQuery
    ).ainvoke(
        [
            SystemMessage(
                content="""
                    You need to generate a query that can retrieve
                    missing information required to select a tool.

                    Return a concise search query.
                    """),
            HumanMessage(
                content=f"""
                        Task:
                        {json.dumps(task, indent=2)}

                        Dependency Outputs:
                        {json.dumps(contexts, indent=2, default=str)}

                        Validation Error:
                        {validation_error}

                        Available Tools:
                        {json.dumps(available_tools, indent=2)}
                        """
                        ),
        ]))

    query_response= cast(AdditionalContextQuery, query_response)
    llm_query = query_response.query
    if artifacts_key not in state['artifacts']:
        state['artifacts'][artifacts_key] = []
    state['artifacts'][artifacts_key].append(
        ContextQueryExchange(
            context=f"""
            Tool Selection node failed while trying to select tool with for the given task and its dependencies output.
            
            ## Task
            {json.dumps(task, indent=2)}
            
            ## Dependency Ouptuts
            {json.dumps(contexts, indent=2, default=str)}
            
            ## Validation Error: 
            {validation_error} 

            ## Tool Specs: 
            {json.dumps(available_tools, indent=2)}
            """,
            query= llm_query,
            query_response = dict(),
            retry_count= len(state['artifacts'][artifacts_key]) + 1
        )
    )
    
    return {
        "artifacts": state["artifacts"],
        "messages": [
                    AIMessage(
                        content=f"Need additional Information with the following query {llm_query}",
                        additional_kwargs={
                            "node_name": "context_synthesizer",
                            "next_node": "query_node"
                        }
                    )
                ]
    }

def task_context_next_node(state: AgentState):
    last_message = state["messages"][-1]
    
    if not isinstance(last_message, AIMessage):
        return "response_synthesizer"

    next_node = last_message.additional_kwargs.get("next_node")

    if next_node is None:
        return "END"

    return next_node
