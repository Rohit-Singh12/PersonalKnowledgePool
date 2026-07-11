import json
import logging

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)

from schemas.state import AgentState
from utilities.load_model import load_models
from utilities.retry_helper import (
    llm_call_with_retry,
    NodeExecutionError,
    MAX_RETRY_COUNT,
)

logger = logging.getLogger(__name__)


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

# Used as the last-resort response if the synthesizer LLM itself fails after
# all retries.  This node must NEVER raise an unhandled exception.
_FALLBACK_RESPONSE = (
    "I encountered an unexpected error while preparing your response. "
    "Please try again. If the issue persists, consider rephrasing your "
    "request or checking the system logs for more details."
)


async def response_synthesizer_node(state: AgentState):
    logger.info(
        "Starting response_synthesizer_node with %s messages", len(state["messages"])
    )
    llm = load_models("Synthesizer")

    conversation = "\n\n".join(
        f"{msg.__class__.__name__}: {msg.content}" for msg in state["messages"]
    )

    node_errors = state.get("node_errors", [])
    needs_user_input = state.get("needs_user_input", False)

    error_section = ""
    if node_errors:
        error_section = (
            "\n\n## Errors Encountered During Execution\n"
            + json.dumps(node_errors, indent=2)
        )

    user_guidance_section = ""
    if needs_user_input:
        user_guidance_section = (
            "\n\n## IMPORTANT\n"
            "The workflow could not complete automatically. "
            "You MUST ask the user for the specific clarification or additional "
            "information needed to proceed. Be explicit about what is missing."
        )

    logger.info(
        "Preparing final response LLM call "
        "(node_errors=%s, needs_user_input=%s)",
        len(node_errors),
        needs_user_input,
    )

    async def make_synthesis_call():
        messages = state["messages"]
        return await llm.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                
            ] + 
            messages
        )

    try:
        response = await llm_call_with_retry(
            "response_synthesizer",
            make_synthesis_call,
            max_retries=MAX_RETRY_COUNT,
        )
        final_text: str = response.content
        logger.info("Completed response_synthesizer_node successfully")

    except NodeExecutionError as e:
        # Last-resort: never allow this node to raise — the user must always
        # receive some response even if it is the hardcoded fallback.
        logger.error(
            "Response synthesizer permanently failed [%s]: %s. "
            "Returning hardcoded fallback.",
            e.error_type.value,
            e.cause,
            exc_info=True,
        )
        final_text = _FALLBACK_RESPONSE

    return {
        "final_response": final_text,
        "messages": [
            AIMessage(
                content=final_text,
                additional_kwargs={
                    "node_name": "response_synthesizer",
                    "next_node": None,
                },
            )
        ],
    }