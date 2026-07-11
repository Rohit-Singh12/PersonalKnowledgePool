import json
import logging
import uuid

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)
from typing import cast
from pydantic import BaseModel

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
from utilities.retry_helper import (
    llm_call_with_retry,
    NodeExecutionError,
    make_error_event,
    MAX_RETRY_COUNT,
)

logger = logging.getLogger(__name__)

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
    logger.info(
        "Starting context_synthesizer_node for current_task_id=%s",
        state.get("current_task_id"),
    )
    task = get_task(state, state["current_task_id"])

    assert task is not None
    assert dependencies_satisfied(task, state)

    contexts = build_task_context(task, state)
    available_tools = await get_tool_specs()
    logger.info("Built task context and loaded %s available tools", len(available_tools))

    llm = load_models("Planner")

    artifacts_key = f'{task.get("id")}_{task["type"]}'
    additional_contexts = state["artifacts"].get(artifacts_key, None)

    if (
        additional_contexts is not None
        and additional_contexts[-1]["retry_count"] >= MAX_RETRY_COUNT
    ):
        logger.warning(
            "Max query-resolver retries (%s) reached for task '%s' — escalating to synthesizer",
            MAX_RETRY_COUNT,
            task.get("id"),
        )
        error_event = {
            "node":       "context_synthesizer",
            "error_type": "max_retries_exceeded",
            "message":    (
                f"Task '{task['description']}' exhausted {MAX_RETRY_COUNT} "
                "query-resolver cycles without a valid tool selection."
            ),
            "attempt":    MAX_RETRY_COUNT,
            "timestamp":  __import__("datetime").datetime.utcnow().isoformat(),
        }
        return {
            "current_task_id": None,
            "needs_user_input": True,
            "node_errors": [error_event],
            "messages": [
                AIMessage(
                    content=(
                        f"Task '{task['description']}' could not be executed after "
                        f"{MAX_RETRY_COUNT} query-resolver cycles. "
                        f"Human assistance is required."
                    ),
                    additional_kwargs={
                        "node_name": "context_synthesizer",
                        "next_node": "response_synthesizer",
                    },
                )
            ],
        }

    formatted_system_prompt = SYSTEM_TEMPLATE.format(
        context=json.dumps(contexts, indent=2, default=str),
        tool_specs=json.dumps(available_tools, indent=2, default=str),
        previous_queries=json.dumps(additional_contexts),
    )

    validation_error: str = ""
    response = None
    llm_node_error: NodeExecutionError | None = None

    # Each iteration asks the LLM to select a tool (with its own internal
    # retry/back-off via llm_call_with_retry) and then validates the choice.
    # Separate concerns: inner retries = transient LLM errors;
    #                    outer loop    = schema / tool-existence errors.
    for attempt in range(MAX_RETRY_COUNT):
        logger.info(
            "Running context synthesis validation attempt %s/%s",
            attempt + 1,
            MAX_RETRY_COUNT,
        )

        # Snapshot current validation_error for this iteration's closure
        validation_error_snapshot = validation_error
        messages = [
            SystemMessage(content=formatted_system_prompt),
            HumanMessage(
                content=f"""
                Current task:

                {json.dumps(task, indent=2)}

                Previous validation error:
                {validation_error_snapshot if validation_error_snapshot else "None"}

                Select the best tool and generate valid arguments.
                """
            ),
        ]

        async def make_tool_selection_call(msgs=messages) -> ToolSelection:
            return cast(
                ToolSelection,
                await llm.with_structured_output(ToolSelection).ainvoke(msgs),
            )

        try:
            response = await llm_call_with_retry(
                "context_synthesizer",
                make_tool_selection_call,
                max_retries=MAX_RETRY_COUNT,
            )
        except NodeExecutionError as e:
            logger.error(
                "Context synthesizer LLM call failed permanently [%s]: %s",
                e.error_type.value,
                e.cause,
            )
            llm_node_error = e
            break  # fall through to query generation with LLM failure context

        #  Not ready - ask query_resolver for more context 
        if not response.ready:
            logger.info(
                "Context synthesizer: LLM response not ready — generating follow-up query"
            )
            break

        # Tool must exist
        tool = await get_tool(response.tool_name)  # type: ignore[arg-type]

        if tool is None:
            validation_error = f"Tool '{response.tool_name}' does not exist."
            logger.warning("Context synthesizer: %s", validation_error)
            continue

        #  Schema validation 
        try:
            if (
                hasattr(tool, "args_schema")
                and tool.args_schema
                and isinstance(tool.args_schema, type)
                and issubclass(tool.args_schema, BaseModel)
            ):
                tool.args_schema.model_validate(response.tool_arguments or {})
            validation_error = ""  # clear on success

        except Exception as e:
            validation_error = str(e)
            logger.warning(
                "Context synthesizer: schema validation failed: %s", validation_error
            )
            response.ready = False
            response.reasoning = (
                f"{response.reasoning}\n\nSchema validation failed:\n{validation_error}"
            )
            continue

        #  All checks passed — dispatch to tool_call node 
        tool_call_id = f"manual_{uuid.uuid4().hex[:8]}"
        tool_schema = ToolCall(
            tool_name=response.tool_name,  # type: ignore[arg-type]
            args=response.tool_arguments,
            tool_call_id=tool_call_id,
        )

        logger.info(
            "Context synthesizer: dispatching tool call to '%s'",
            tool_schema["tool_name"],
        )
        return {
            "selected_tool_name": tool_schema,
            "messages": [
                AIMessage(
                    content=f"Tool Call to tool {tool_schema['tool_name']}",
                    additional_kwargs={
                        "node_name": "context_synthesizer",
                        "next_node": "tool_call",
                    },
                    tool_calls=[
                        {
                            "name": tool_schema["tool_name"],
                            "args": tool_schema["args"],
                            "id": tool_call_id,
                        }
                    ],
                )
            ],
        }

    # Could not select a tool — generate a follow-up query for query_resolver.
    # If the LLM itself was broken, inject that context into the query prompt.

    artifacts = dict(state["artifacts"])
    if artifacts_key not in artifacts:
        artifacts[artifacts_key] = []

    llm_failure_note = (
        f"\nLLM call also failed with [{llm_node_error.error_type.value}]: "
        f"{llm_node_error.cause}"
        if llm_node_error
        else ""
    )

    logger.info("Preparing follow-up query generation LLM call")

    query_messages = [
        SystemMessage(
            content="""
            You need to generate a query that can retrieve
            missing information required to select a tool.

            Return a concise search query.
            """
        ),
        HumanMessage(
            content=f"""
            Task:
            {json.dumps(task, indent=2)}

            Dependency Outputs:
            {json.dumps(contexts, indent=2, default=str)}

            Validation Error:
            {validation_error}{llm_failure_note}

            Available Tools:
            {json.dumps(available_tools, indent=2)}
            """
        ),
    ]

    async def make_query_call(msgs=query_messages) -> AdditionalContextQuery:
        return cast(
            AdditionalContextQuery,
            await llm.with_structured_output(AdditionalContextQuery).ainvoke(msgs),
        )

    try:
        query_response = await llm_call_with_retry(
            "context_synthesizer_query",
            make_query_call,
            max_retries=MAX_RETRY_COUNT,
        )
    except NodeExecutionError as qe:
        logger.error(
            "Context synthesizer query generation failed permanently [%s]: %s",
            qe.error_type.value,
            qe.cause,
        )
        node_errors: list[dict] = [
            make_error_event(
                "context_synthesizer_query", qe.cause, qe.error_type, MAX_RETRY_COUNT
            )
        ]
        if llm_node_error:
            node_errors.insert(
                0,
                make_error_event(
                    "context_synthesizer",
                    llm_node_error.cause,
                    llm_node_error.error_type,
                    MAX_RETRY_COUNT,
                ),
            )
        return {
            "artifacts": artifacts,
            "needs_user_input": True,
            "node_errors": node_errors,
            "messages": [
                AIMessage(
                    content=(
                        f"Context synthesizer could not generate a follow-up query "
                        f"for task '{task['description']}'. "
                        f"Error: {qe.cause}"
                    ),
                    additional_kwargs={
                        "node_name": "context_synthesizer",
                        "next_node": "response_synthesizer",
                    },
                )
            ],
        }

    llm_query = query_response.query
    logger.info("Received additional context query: %s", llm_query)

    # Collect any LLM errors to propagate via node_errors
    node_errors_out: list[dict] = []
    if llm_node_error:
        node_errors_out.append(
            make_error_event(
                "context_synthesizer",
                llm_node_error.cause,
                llm_node_error.error_type,
                MAX_RETRY_COUNT,
            )
        )

    artifacts[artifacts_key].append(
        ContextQueryExchange(
            context=f"""
            Tool Selection node failed while trying to select a tool for the given task
            and its dependency outputs.

            ## Task
            {json.dumps(task, indent=2)}

            ## Dependency Outputs
            {json.dumps(contexts, indent=2, default=str)}

            ## Validation Error
            {validation_error}{llm_failure_note}

            ## Tool Specs
            {json.dumps(available_tools, indent=2)}
            """,
            query=llm_query,
            query_response=dict(),
            retry_count=len(artifacts[artifacts_key]) + 1,
        )
    )

    logger.info("Completed context_synthesizer_node and recorded follow-up query")
    return {
        "artifacts": artifacts,
        "node_errors": node_errors_out,
        "messages": [
            AIMessage(
                content=f"Need additional information with the following query: {llm_query}",
                additional_kwargs={
                    "node_name": "context_synthesizer",
                    "next_node": "query_node",
                },
            )
        ],
    }


def task_context_next_node(state: AgentState) -> str:
    logger.info(
        "Determining next node from last message type=%s",
        type(state["messages"][-1]).__name__,
    )
    last_message = state["messages"][-1]

    if not isinstance(last_message, AIMessage):
        return "response_synthesizer"

    next_node = last_message.additional_kwargs.get("next_node")

    if next_node is None:
        return "END"

    return next_node
