import json

from langchain_core.messages import ToolMessage

from schemas.state import (
    AgentState,
    WorkerTrace,
)

from utilities.tools_helper import get_tool
from utilities.dependency_helper import get_task


async def tool_node(state: AgentState):

    task = get_task(
        state,
        state["current_task_id"]
    )

    assert task is not None

    tool = state['selected_tool_name']
    assert tool is not None
    tool_name = tool["tool_name"]
    tool_arguments = tool['args']
    tool_call_id = tool["tool_call_id"]

    if tool_name is None:
        raise ValueError(
            "selected_tool missing from state"
        )

    tool = await get_tool(tool_name)  # type: ignore

    if tool is None:
        raise ValueError(
            f"Tool '{tool_name}' not found"
        )

    task["status"] = "running"

    try:

        if hasattr(tool, "ainvoke"):

            result = await tool.ainvoke(
                tool_arguments or {}
            )

        else:

            result = tool.invoke(
                tool_arguments or {}
            )

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
            "worker_traces": (
                state["worker_traces"] + [trace]
            ),
            "messages": [
                ToolMessage(
                    content=json.dumps(
                        result,
                        indent=2,
                        default=str,
                    ),
                    name=tool_name,
                    additional_kwargs={
                        "node_name": "tool_call",
                        "next_node": "next_task"
                    },
                    tool_call_id=tool_call_id
                )
            ]
        }

    except Exception as e:

        task["status"] = "failed"
        task["error"] = str(e)

        trace: WorkerTrace = {
            "task": task,
            "dependency_results": [],
            "artifacts": {
                "tool": tool_name,
                "arguments": tool_arguments,
                "error": str(e),
            },
            "messages": [],
            "output_schema": None,
        }

        return {
            "tasks": state["tasks"],
            "worker_traces": (
                state["worker_traces"] + [trace]
            ),
            "messages": [
                ToolMessage(
                    content=f"Tool execution failed: {e}",
                    name=tool_name,
                    additional_kwargs={
                        "node_name": "tool_call",
                        "next_node": "next_task"
                    },
                    tool_call_id=tool_call_id
                )
            ]
        }