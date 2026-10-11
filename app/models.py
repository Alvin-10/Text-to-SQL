"""API request/response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Natural-language question.")


class QueryResponse(BaseModel):
    sql: str = Field(..., description="The validated SQL that was executed.")
    columns: list[str] = Field(default_factory=list)
    results: list[dict[str, Any]] = Field(default_factory=list)
    explanation: str = Field("", description="Natural-language summary of the result.")
    row_count: int = 0
    attempts: int = Field(1, description="Number of generation attempts used.")


class ErrorResponse(BaseModel):
    detail: str
    attempts: int = 0
    last_sql: str | None = None
