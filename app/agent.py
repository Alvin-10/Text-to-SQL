"""Agent orchestrator + self-correction loop (component [5]).

Ties the pieces together:
  question -> generate SQL -> validate -> execute -> (retry on error) -> summarise
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy.engine import Engine

from . import prompt
from .executor import ExecutionError, execute
from .llm import LLM, LLMError
from .schema_introspector import SchemaStore, allowed_table_names, render_for_prompt
from .validator import SQLValidationError, validate_and_normalize

logger = logging.getLogger("text2sql.agent")


class AgentError(Exception):
    """Raised when the agent exhausts its retries without a valid result."""

    def __init__(self, message: str, attempts: int, last_sql: str | None) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.last_sql = last_sql


@dataclass
class AgentResult:
    sql: str
    columns: list[str]
    rows: list[dict[str, Any]]
    explanation: str
    attempts: int


class TextToSQLAgent:
    def __init__(
        self,
        llm: LLM,
        schema_store: SchemaStore,
        readonly_engine: Engine,
        *,
        max_retries: int,
        max_rows: int,
        default_limit: int,
        dialect: str = "postgres",
        dialect_label: str = "PostgreSQL",
    ) -> None:
        self._llm = llm
        self._schema_store = schema_store
        self._engine = readonly_engine
        self._max_retries = max_retries
        self._max_rows = max_rows
        self._default_limit = default_limit
        self._dialect = dialect
        self._dialect_label = dialect_label

    def answer(self, question: str) -> AgentResult:
        schema = self._schema_store.get()
        allowed = allowed_table_names(schema)
        system = prompt.build_system_prompt(
            render_for_prompt(schema), self._dialect_label
        )

        messages: list[dict[str, str]] = [
            {"role": "user", "content": prompt.build_user_prompt(question)}
        ]

        last_error: str | None = None
        last_sql: str | None = None

        # 1 initial attempt + max_retries correction attempts.
        for attempt in range(1, self._max_retries + 2):
            try:
                raw = self._llm.complete(system, messages, max_tokens=1024)
            except LLMError as exc:
                raise AgentError(str(exc), attempts=attempt, last_sql=last_sql) from exc

            candidate = prompt.extract_sql(raw)
            last_sql = candidate

            try:
                safe_sql = validate_and_normalize(
                    candidate,
                    allowed_tables=allowed,
                    max_rows=self._max_rows,
                    default_limit=self._default_limit,
                    dialect=self._dialect,
                )
                columns, rows = execute(safe_sql, self._engine, self._max_rows)
            except (SQLValidationError, ExecutionError) as exc:
                last_error = str(exc)
                logger.info("attempt %d failed: %s", attempt, last_error)
                messages.append({"role": "assistant", "content": raw})
                messages.append(
                    {"role": "user", "content": prompt.build_correction_prompt(last_error)}
                )
                continue

            explanation = self._summarise(question, safe_sql, columns, rows)
            return AgentResult(
                sql=safe_sql,
                columns=columns,
                rows=rows,
                explanation=explanation,
                attempts=attempt,
            )

        raise AgentError(
            f"Failed to produce a valid query after {self._max_retries + 1} attempts. "
            f"Last error: {last_error}",
            attempts=self._max_retries + 1,
            last_sql=last_sql,
        )

    def _summarise(
        self,
        question: str,
        sql: str,
        columns: list[str],
        rows: list[dict[str, Any]],
    ) -> str:
        """Best-effort NL summary; falls back to a template if the call fails."""
        system, user = prompt.build_summary_prompt(question, sql, columns, rows)
        try:
            return self._llm.complete(
                system, [{"role": "user", "content": user}], max_tokens=300
            )
        except LLMError:
            noun = "row" if len(rows) == 1 else "rows"
            return f"Returned {len(rows)} {noun}."
