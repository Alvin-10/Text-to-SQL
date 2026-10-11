"""Component [4]: Sandboxed execution.

Runs validated SQL against the read-only engine (SELECT-only role +
statement_timeout), caps the number of rows read, and returns
JSON-serialisable results.
"""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Engine


class ExecutionError(Exception):
    """Raised when a query fails to execute (including timeouts)."""


def _clean(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (_dt.datetime, _dt.date, _dt.time)):
        return value.isoformat()
    if isinstance(value, (bytes, memoryview)):
        return bytes(value).decode("utf-8", errors="replace")
    return value


def execute(
    sql: str, engine: Engine, max_rows: int
) -> tuple[list[str], list[dict[str, Any]]]:
    """Execute ``sql`` and return ``(columns, rows)``.

    Reads at most ``max_rows`` rows. Raises :class:`ExecutionError` on any
    database error, including a ``statement_timeout`` cancellation.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            columns = list(result.keys())
            raw_rows = result.fetchmany(max_rows)
    except SQLAlchemyError as exc:
        # Surface the DB message (e.g. "canceling statement due to timeout")
        # so the self-correction loop can feed it back to the LLM.
        message = str(getattr(exc, "orig", exc)).strip()
        raise ExecutionError(message) from exc

    rows = [
        {col: _clean(val) for col, val in zip(columns, row)} for row in raw_rows
    ]
    return columns, rows
