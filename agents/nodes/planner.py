import json
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)

from schemas.state import AgentState
from schemas.planner_output import Plan
from utilities.load_model import load_models
from utilities.tools_helper import get_tool_specs
from langchain_core.prompts import PromptTemplate


PLANNER_SYSTEM_PROMPT = PromptTemplate.from_template("""
You are a planning agent.

Available tools Specifications:

{tool_specs}

Previous Converstation Context:
{context}

Rules:
1. Decompose the request into the minimum number of tasks.
2. Add dependencies when a task requires outputs from another task.
3. Tasks should form a DAG (Directed Acyclic Graph). Make sure there is no cyclic dependency.
4. Every task must have:
    - id
    - type
    - description
    - dependencies
5. Return JSON only.

Example:
User:
Research LangGraph.

Output:
{{
  "tasks": [
    {{
      "id": "1",
      "type": "WEB_SEARCH",
      "description": "Find LangGraph articles",
      "dependencies": []
    }},
    {{
      "id": "2",
      "type": "SCRAPE_URL",
      "description": "Scrape URLs from task 1",
      "dependencies": ["1"]
    }}
  ]
}}
""")


async def planner_node(state: AgentState):

    user_query = state["messages"][-1].content
    planner_llm = load_models('Planner')
    specs = await get_tool_specs()
    planner_prompt = PLANNER_SYSTEM_PROMPT.format(tool_specs=specs, context=state['messages'])
    plan = await planner_llm.with_structured_output(
        Plan
    ).ainvoke(
        [
            SystemMessage(
                content=planner_prompt
            ),
            HumanMessage(
                content=user_query
            )
        ]
    )

    tasks = []

    for t in plan.tasks:  # type: ignore
        
        tasks.append(
            {
                "id": t.id,
                "type": t.type,
                "description": t.description,
                "dependencies": t.dependencies,
                "inputs": t.inputs,
                "status": "pending",
                "result": None,
                "error": None,
            }
        )
    
    return {
        "tasks": tasks,
        "messages": [
            AIMessage(
                content=f"Created execution plan:\n\n{json.dumps(tasks, indent=2)}",
                additional_kwargs={
                    "node_name": "planner",
                    "next_node": "next_task"
                }
            )
        ],
    }