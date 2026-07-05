from schemas.state import AgentState
from utilities.dependency_helper import get_task

def task_router(
    state: AgentState
):

    task_id = state["current_task_id"]

    if task_id is None:
        return "synthesizer"

    task = get_task(
        state,
        task_id
    )

    return task["type"]