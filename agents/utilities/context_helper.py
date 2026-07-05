from schemas.state import AgentState, Task
from utilities.dependency_helper import get_task
from typing import List

def build_task_context(
    task: Task,
    state: AgentState,
) -> List[dict]:

    context: List[dict] = []

    for dep_id in task["dependencies"]:

        dep_task = get_task(
            state,
            dep_id
        )

        context.append(
            {
                "task_id": dep_id,
                "description": dep_task["description"],
                "result": dep_task["result"],
            }
        )

    return context
