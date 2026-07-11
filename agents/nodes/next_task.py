import logging

from langchain_core.messages import AIMessage
from utilities.dependency_helper import next_task
from schemas.state import AgentState

logger = logging.getLogger(__name__)


async def next_task_node(state: AgentState):
    logger.info(
        "Starting next_task_node for state with current_task_id=%s",
        state.get("current_task_id"),
    )

    # Do not attempt to find the next task — route straight to the synthesizer
    # so it can explain the situation and ask the user for what is needed.
    if state.get("needs_user_input"):
        logger.info(
            "needs_user_input=True detected — short-circuiting to response_synthesizer"
        )
        return {
            "current_task_id": None,
            "messages": [
                AIMessage(
                    content="Workflow aborted: human assistance is required.",
                    additional_kwargs={
                        "node_name": "next_task",
                        "next_node": "response_synthesizer",
                    },
                )
            ],
        }

    try:
        task = await next_task(state)
    except Exception as e:
        logger.error(
            "next_task raised an unexpected error: %s", e, exc_info=True
        )
        return {
            "current_task_id": None,
            "messages": [
                AIMessage(
                    content=f"Failed to determine the next task: {e}",
                    additional_kwargs={
                        "node_name": "next_task",
                        "next_node": "response_synthesizer",
                    },
                )
            ],
        }

    logger.info("Resolved next task: %s", task)

    return {
        "current_task_id": task["id"] if task else None,
        "messages": [
            AIMessage(
                content=(
                    f"Next task to be executed is the task with id {task['id']}"
                    if task
                    else "All tasks completed."
                ),
                additional_kwargs={
                    "node_name": "next_task",
                    "next_node": (
                        "response_synthesizer" if task is None else "context_synthesizer"
                    ),
                },
            )
        ],
    }


def route_next_node(state: AgentState) -> str:
    logger.info(
        "Routing from next_task (needs_user_input=%s, current_task_id=%s)",
        state.get("needs_user_input"),
        state.get("current_task_id"),
    )

    if state.get("needs_user_input"):
        return "response_synthesizer"

    if state.get("current_task_id") is None:
        return "response_synthesizer"

    return "context_synthesizer"
