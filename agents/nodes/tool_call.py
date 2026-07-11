import json
import logging

from langchain_core.messages import ToolMessage

from schemas.state import (
    AgentState,
    WorkerTrace,
)

from utilities.tools_helper import get_tool
from utilities.dependency_helper import get_task
from utilities.retry_helper import (
    llm_call_with_retry,
    NodeExecutionError,
    make_error_event,
    MAX_RETRY_COUNT,
)

logger = logging.getLogger(__name__)


async def tool_node(state: AgentState):
    logger.info(
        "Starting tool_node for current_task_id=%s", state.get("current_task_id")
    )
    task = get_task(state, state["current_task_id"])
    assert task is not None

    tool_meta = state["selected_tool_name"]
    assert tool_meta is not None

    tool_name = tool_meta["tool_name"]
    tool_arguments = tool_meta["args"]
    tool_call_id = tool_meta["tool_call_id"]

    if tool_name is None:
        raise ValueError("selected_tool missing from state")

    logger.info(
        "Preparing to execute tool '%s' with arguments: %s",
        tool_name,
        tool_arguments,
    )
    tool = await get_tool(tool_name)  # type: ignore[arg-type]

    if tool is None:
        raise ValueError(f"Tool '{tool_name}' not found")

    task["status"] = "running"

    async def make_tool_call():
        if hasattr(tool, "ainvoke"):
            return await tool.ainvoke(tool_arguments or {})
        return tool.invoke(tool_arguments or {})

    try:
        # pre_call_delay_seconds=0 — tool calls do not need the LLM rate-limit
        # guard; back-off still applies on TIMEOUT / RATE_LIMIT errors.
        result = await llm_call_with_retry(
            f"tool_call[{tool_name}]",
            make_tool_call,
            max_retries=MAX_RETRY_COUNT,
            pre_call_delay_seconds=0,
        )

        logger.info("Tool '%s' completed successfully", tool_name)
        task["status"] = "completed"
        task["result"] = result
        task["error"] = None

        trace: WorkerTrace = {
            "task": task,
            "dependency_results": [],
            "artifacts": {
                "tool": tool_name,
                "arguments": tool_arguments,
                "result": result,
            },
            "messages": [],
            "output_schema": None,
        }

        return {
            "tasks": state["tasks"],
            "worker_traces": state["worker_traces"] + [trace],
            "messages": [
                ToolMessage(
                    content=json.dumps(result, indent=2, default=str),
                    name=tool_name,
                    additional_kwargs={
                        "node_name": "tool_call",
                        "next_node": "next_task",
                    },
                    tool_call_id=tool_call_id,
                )
            ],
        }

    except NodeExecutionError as e:
        logger.error(
            "Tool '%s' permanently failed after retries [%s]: %s",
            tool_name,
            e.error_type.value,
            e.cause,
            exc_info=True,
        )

        task["status"] = "failed"
        task["error"] = str(e.cause)
        error_event = make_error_event(
            f"tool_call[{tool_name}]", e.cause, e.error_type, MAX_RETRY_COUNT
        )

        trace: WorkerTrace = {
            "task": task,
            "dependency_results": [],
            "artifacts": {
                "tool": tool_name,
                "arguments": tool_arguments,
                "error": str(e.cause),
                "error_type": e.error_type.value,
            },
            "messages": [],
            "output_schema": None,
        }

        return {
            "tasks": state["tasks"],
            "worker_traces": state["worker_traces"] + [trace],
            "node_errors": [error_event],
            "messages": [
                ToolMessage(
                    content=(
                        f"Tool '{tool_name}' failed after "
                        f"{MAX_RETRY_COUNT + 1} attempts "
                        f"[{e.error_type.value}]: {e.cause}"
                    ),
                    name=tool_name,
                    additional_kwargs={
                        "node_name": "tool_call",
                        "next_node": "next_task",
                    },
                    tool_call_id=tool_call_id,
                )
            ],
        }