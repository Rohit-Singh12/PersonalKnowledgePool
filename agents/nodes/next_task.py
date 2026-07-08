import logging

from langchain_core.messages import AIMessage
from utilities.dependency_helper import next_task
from schemas.state import AgentState

logger = logging.getLogger(__name__)


async def next_task_node(state: AgentState):
    logger.info("Starting next_task_node for state with current_task_id=%s", state.get("current_task_id"))
    task = await next_task(state)
    logger.info("Resolved next task: %s", task)

    return {
        "current_task_id": task["id"] if task else None,
        "messages": [
            AIMessage(
                content=f"Next task to be executed is the task with id {task['id']}" if task else "All task completed.",
                additional_kwargs={
                    "node_name": "next_task",
                    "next_node": "response_synthesizer" if (task is None) else "context_synthesizer"
                }
            )
        ]
    }


def route_next_node(state: AgentState) -> str:
    logger.info("Routing next node from current_task_id=%s", state.get("current_task_id"))
    if state.get("current_task_id") is None:
        return "response_synthesizer"

    return "context_synthesizer"

