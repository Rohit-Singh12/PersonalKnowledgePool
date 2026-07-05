from pydantic import BaseModel
from typing import Any


class SchemaResponse(BaseModel):
    tables: dict[str, Any]


class QueryResponse(BaseModel):
    rows: list[dict[str, Any]]
    row_count: int


class WriteResponse(BaseModel):
    row_count: int
    success: bool