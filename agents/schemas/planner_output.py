from pydantic import BaseModel, Field


class PlannedTask(BaseModel):
    id: str

    type: str

    description: str

    dependencies: list[str] = Field(default_factory=list)

    inputs: dict = Field(default_factory=dict)


class Plan(BaseModel):
    tasks: list[PlannedTask]