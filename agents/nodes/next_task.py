from langchain_core.messages import AIMessage
from utilities.dependency_helper import next_task
from schemas.state import AgentState

async def next_task_node(state: AgentState):
    task = await next_task(state)
    
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
    if state.get("current_task_id") is None:
        return "response_synthesizer"

    return "context_synthesizer"
    
