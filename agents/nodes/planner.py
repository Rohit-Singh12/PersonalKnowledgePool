import json
import logging

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)

from schemas.state import AgentState
from schemas.planner_output import Plan
from utilities.load_model import load_models
from utilities.tools_helper import get_tool_specs
from utilities.retry_helper import (
    llm_call_with_retry,
    NodeExecutionError,
    make_error_event,
    MAX_RETRY_COUNT,
    ErrorType,
)
from langchain_core.prompts import PromptTemplate

logger = logging.getLogger(__name__)


PLANNER_SYSTEM_PROMPT = PromptTemplate.from_template("""
You are a planning agent.

Available tools Specifications:

{tool_specs}

Previous Converstation Context:
{context}

{error_context}

Rules:
1. Decompose the request into the minimum number of tasks.
2. Add dependencies when a task requires outputs from another task.
3. Tasks should form a DAG (Directed Acyclic Graph). Make sure there is no cyclic dependency.
4. Every task must have:
    - id
    - type
    - description
    - dependencies
5. Return JSON only.

Example:
User:
Research LangGraph.

Output:
{{
  "tasks": [
    {{
      "id": "1",
      "type": "WEB_SEARCH",
      "description": "Find LangGraph articles",
      "dependencies": []
    }},
    {{
      "id": "2",
      "type": "SCRAPE_URL",
      "description": "Scrape URLs from task 1",
      "dependencies": ["1"]
    }}
  ]
}}
""")


async def planner_node(state: AgentState):
    logger.info("Starting planner_node with message count=%s", len(state["messages"]))

    user_query = state["messages"][-1].content
    logger.info("Preparing planner request for user query: %s", user_query)

    planner_llm = load_models('Planner')
    specs = await get_tool_specs()
    logger.info("Loaded %s tool specs for planning", len(specs))

    error_context: list[str] = [""]

    def on_retry(e: Exception, error_type: ErrorType, attempt: int) -> None:
        """Append failure details so the next prompt can self-correct."""
        error_context[0] += (
            f"\nPrevious attempt {attempt + 1} failed "
            f"[{error_type.value}]: {str(e)}\n"
            f"Please refine your plan and avoid repeating this issue.\n"
        )

    async def make_planner_call() -> Plan:
        planner_prompt = PLANNER_SYSTEM_PROMPT.format(
            tool_specs=specs,
            context=state["messages"],
            error_context=error_context[0],
        )
        return await planner_llm.with_structured_output(Plan).ainvoke(  # type: ignore[return-value]
            [
                SystemMessage(content=planner_prompt),
                HumanMessage(content=user_query),
            ]
        )

    try:
        plan = await llm_call_with_retry(
            "planner",
            make_planner_call,
            max_retries=MAX_RETRY_COUNT,
            on_retry=on_retry,
        )

        tasks = []
        for t in plan.tasks:  # type: ignore[union-attr]
            tasks.append(
                {
                    "id": t.id,
                    "type": t.type,
                    "description": t.description,
                    "dependencies": t.dependencies,
                    "inputs": t.inputs,
                    "status": "pending",
                    "result": None,
                    "error": None,
                }
            )

        logger.info("Completed planner_node and created %s task entries", tasks)
        return {
            "tasks": tasks,
            "messages": [
                AIMessage(
                    content=f"Created execution plan:\n\n{json.dumps(tasks, indent=2)}",
                    additional_kwargs={
                        "node_name": "planner",
                        "next_node": "next_task",
                    },
                )
            ],
        }

    except NodeExecutionError as e:
        logger.error(
            "Planner permanently failed [%s]: %s",
            e.error_type.value,
            e.cause,
            exc_info=True,
        )
        error_event = make_error_event("planner", e.cause, e.error_type, MAX_RETRY_COUNT)

        return {
            "tasks": [],
            "needs_user_input": True,
            "node_errors": [error_event],
            "messages": [
                AIMessage(
                    content=(
                        f"Planning failed after {MAX_RETRY_COUNT + 1} attempts "
                        f"due to a {e.error_type.value} error. "
                        f"Error details: {str(e.cause)}\n\n"
                        f"Accumulated retry context:\n{error_context[0]}"
                    ),
                    additional_kwargs={
                        "node_name": "planner",
                        "next_node": "response_synthesizer",
                    },
                )
            ],
        }