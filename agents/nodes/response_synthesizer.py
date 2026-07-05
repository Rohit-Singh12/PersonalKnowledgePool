from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)

from schemas.state import AgentState
from utilities.load_model import load_models


SYSTEM_PROMPT = """
You are the final response synthesizer.

Your job is to produce the final response for the user based on the
entire workflow execution.

Guidelines:
- Use information from previous tool outputs and reasoning steps.
- Do not expose internal planner decisions.
- Do not mention node names, routing logic, retries, or tool selection.
- Provide a concise but complete answer.
- If the workflow could not complete successfully, explain what
  information is still needed from the user.
- Output only the final response intended for the user.
"""


async def response_synthesizer_node(state: AgentState):
    llm = load_models("Synthesizer")

    conversation = "\n\n".join(
        [
            f"{msg.__class__.__name__}: {msg.content}"
            for msg in state["messages"]
        ]
    )

    response = await llm.ainvoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=f"""
                Conversation History:

                {conversation}

                Generate the final response for the user.
                """
            ),
        ]
    )

    return {
        "messages": [
            AIMessage(
                content=response.content,
                additional_kwargs={
                    "node_name": "response_synthesizer",
                    "next_node": None,
                },
            )
        ]
    }