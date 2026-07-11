import asyncio
import logging
import sys
import uuid

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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Remove logs from these packages
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("mcp").setLevel(logging.WARNING)

CHECKPOINT_DB_PATH = "/home/appuser/checkpoints.sqlite"


async def build_graph(checkpointer=None):
    # if checkpointer is None:
    # CHECKPOINT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
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


async def run_agent_step(app, checkpointer, message: str, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    checkpoint = await checkpointer.aget(config)
    
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
        node_errors=[],          
        needs_user_input=False,
    )
    
    final_state = await app.ainvoke(state, config=config)
    return final_state


async def interactive_session():
    # CHECKPOINT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # 1. Open connection to SQLite
    async with AsyncSqliteSaver.from_conn_string(str(CHECKPOINT_DB_PATH)) as checkpointer:
        # 2. Compile the graph once
        app = await build_graph(checkpointer)
        
        # 3. Create or fetch a unique thread ID for this session
        # You can also pass this as a command line argument if you want to resume a previous one.
        thread_id = str(uuid.uuid4())[:8] 
        
        print("\n" + "="*50)
        print(f"LangGraph Agent Session Initialized!")
        print(f"Thread ID: {thread_id}")
        print("Type 'exit', 'quit', or 'q' to end the chat.")
        print("="*50 + "\n")

        # 4. Infinite interactive loop
        while True:
            # Using asyncio loop to read input without blocking the whole thread
            user_input = await asyncio.to_thread(input, "You: [Type 'exit', 'quit', or 'q' to end the chat]")
            
            if user_input.strip().lower() in ['exit', 'quit', 'q']:
                print("Ending session. Goodbye!")
                break
                
            if not user_input.strip():
                continue

            print("\nThinking...")
            try:
                result = await run_agent_step(app, checkpointer, user_input, thread_id)
                
                # Assuming your response_synthesizer or final node updates 'final_response'
                response = result.get("final_response")
                
                # Fallback: if final_response is empty, print the last message content
                if not response and result.get("messages"):
                    response = result["messages"][-1].content

                print(f"\nAgent: {response}\n")
                print("-" * 30)
                
            except Exception as e:
                print(f"\n Error processing request: {e}\n")


if __name__ == "__main__":
    # Run the interactive loop
    try:
        asyncio.run(interactive_session())
    except KeyboardInterrupt:
        print("\nSession interrupted. Goodbye!")
        sys.exit(0)