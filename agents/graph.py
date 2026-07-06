import asyncio
import sqlite3
from pathlib import Path

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import (
    StateGraph,
    END,
)
from schemas.state import AgentState
from nodes.planner import planner_node
from nodes.next_task import next_task_node, route_next_node
from nodes.task_context import context_synthesizer_node, task_context_next_node
from nodes.response_synthesizer import response_synthesizer_node
from nodes.query_resolver import answer_query_node
from nodes.tool_call import tool_node


CHECKPOINT_DB_PATH = Path(__file__).resolve().parent / "checkpoints.sqlite"


async def build_graph(checkpointer=None):
    # if checkpointer is None:
    CHECKPOINT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    graph = StateGraph(AgentState)

    # NODES
    graph.add_node("planner", planner_node)
    graph.add_node("next_task", next_task_node)
    graph.add_node("context_synthesizer", context_synthesizer_node)
    graph.add_node("response_synthesizer", response_synthesizer_node)
    graph.add_node("query_node", answer_query_node)
    graph.add_node("tool_call", tool_node)

    # EDGES
    graph.set_entry_point("planner")
    graph.add_edge("planner", "next_task")
    graph.add_conditional_edges("next_task", route_next_node)
    graph.add_conditional_edges("context_synthesizer", task_context_next_node)
    graph.add_edge("query_node", "context_synthesizer")
    graph.add_edge("response_synthesizer", END)
    graph.add_edge("tool_call", "next_task")

    return graph.compile(checkpointer=checkpointer)


async def run_agent(message: str, thread_id: str = "default-thread"):
    CHECKPOINT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with AsyncSqliteSaver.from_conn_string(
        str(CHECKPOINT_DB_PATH)
    ) as checkpointer:

        app = await build_graph(checkpointer)
        config = {"configurable": {"thread_id": thread_id}}
        checkpoint = await checkpointer.aget(config)
        print(checkpoint)
        
        if checkpoint:
            state = {
                "messages": [HumanMessage(content=message)]
            }

        state = AgentState(
            messages=[HumanMessage(content=message)],
            artifacts={},
            current_task_id=None,
            final_response="",
            selected_tool_name=None,
            tasks=[],
            worker_traces=[],
        )

        
        return await app.ainvoke(state, config=config)


if __name__ == "__main__":
    print("CALLING STATE")
    final_state = asyncio.run(run_agent(
        "Give the final response from the searches."
    ))
    print(final_state)