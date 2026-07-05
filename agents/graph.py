import asyncio
import sqlite3
from pathlib import Path

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver
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


def build_graph(checkpointer=None):
    if checkpointer is None:
        CHECKPOINT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(CHECKPOINT_DB_PATH)
        checkpointer = SqliteSaver(conn=connection)

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


app = build_graph()


def run_agent(message: str, thread_id: str = "default-thread"):
    state = AgentState(
        messages=[HumanMessage(content=message)],
        artifacts={},
        current_task_id=None,
        final_response="",
        selected_tool_name=None,
        tasks=[],
        worker_traces=[],
    )
    config = {"configurable": {"thread_id": thread_id}}
    return asyncio.run(app.ainvoke(state, config=config))


if __name__ == "__main__":
    print("CALLING STATE")
    final_state = run_agent(
        "Look out for articles on p-value in Machine Learning and Shap values. Save the top 2 articles in database."
    )
    print(final_state)