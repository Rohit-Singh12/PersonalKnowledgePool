from pydantic import BaseModel, Field
from typing import Optional, Any

class ToolSelection(BaseModel):
    ready: bool = Field(description="True if all required dependencies exist, False otherwise.")
    reasoning: str = Field(description="Explanation for why the task is ready or why information is missing.")
    tool_name: Optional[str] = Field(None, description="The name of the tool to execute if ready.")
    tool_arguments: Optional[dict[str, Any]] = Field(None, description="Valid JSON arguments constructed for the tool.")