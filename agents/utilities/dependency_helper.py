from schemas.state import AgentState, Task

def get_task(
    state: AgentState,
    task_id: str | None,
):
    return next(
        t
        for t in state["tasks"]
        if t["id"] == task_id
    )

def dependencies_satisfied(
    task: Task,
    state: AgentState,
):

    for dep_id in task["dependencies"]:

        dep_task = get_task(
            state,
            dep_id
        )

        if dep_task["status"] != "completed":
            return False

    return True

async def next_task(
    state: AgentState
) -> Task | None:

    for task in state["tasks"]:

        if (
            task["status"] == "pending"
            and dependencies_satisfied(
                task,
                state
            )
        ):
            return task

    return None
    
def all_tasks_finished(
    state: AgentState
):

    return all(
        task["status"]
        in ["completed", "failed"]
        for task in state["tasks"]
    )
    
def continue_or_finish(
    state: AgentState
):

    if all_tasks_finished(
        state
    ):
        return "synthesizer"

    return "next_task"