import operator
from typing import Annotated, TypedDict, Literal, Any

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


TaskStatus = Literal[
    "pending",
    "running",
    "completed",
    "failed"
]


class Task(TypedDict):
    id: str
    type: str
    description: str
    dependencies: list[str]
    inputs: dict[str, Any]
    status: TaskStatus
    result: str | dict | list | None
    error: str | None


class WorkerTrace(TypedDict):
    task: Task

    dependency_results: list[Any]

    artifacts: dict[str, Any]

    messages: list[BaseMessage]

    output_schema: dict | None


class ContextQueryExchange(TypedDict):
    context: str

    query: str

    query_response: dict[str, Any]

    retry_count: int

class ToolCall(TypedDict):
    tool_name: str
    args: dict | None
    tool_call_id: str


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

    tasks: list[Task]

    artifacts: dict[str, list[ContextQueryExchange]]

    worker_traces: list[WorkerTrace]

    current_task_id: str | None

    final_response: str | None

    selected_tool_name: ToolCall | None

    # Append-only list of structured error events emitted by any node.
    node_errors: Annotated[list[dict], operator.add]

    # Set to True by any node that cannot continue without user intervention.
    needs_user_input: bool