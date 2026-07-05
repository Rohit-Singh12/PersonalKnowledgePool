from pydantic import BaseModel, Field

class AdditionalContextQuery(BaseModel):
    query: str = Field(
        description="Question to retrieve missing information"
    )