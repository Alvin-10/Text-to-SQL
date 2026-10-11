"""Component [3]: SQL validator / sandbox gate.

Parses the generated SQL with sqlglot and rejects anything that is not a
single read-only SELECT touching only allowed tables. Enforces a LIMIT.

This is the last line of defence *before* the read-only DB role; both must
agree for a query to run.
"""

from __future__ import annotations

import sqlglot
from sqlglot import exp

DEFAULT_DIALECT = "postgres"

# Statement/expression types that write, change structure, or run raw commands.
_FORBIDDEN_TYPES: tuple[type[exp.Expression], ...] = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Merge,
    exp.Drop,
    exp.Create,
    exp.Alter,
    exp.TruncateTable,
    exp.Command,      # e.g. GRANT, SET, VACUUM, CALL, COPY, and other raw commands
    exp.Transaction,  # BEGIN / START TRANSACTION
    exp.Commit,
    exp.Rollback,
)

# Top-level nodes we accept as read-only result-producing queries.
_ALLOWED_ROOTS: tuple[type[exp.Expression], ...] = (
    exp.Select,
    exp.Union,
    exp.Intersect,
    exp.Except,
    exp.Subquery,
)


class SQLValidationError(Exception):
    """Raised when generated SQL fails a safety check."""


def _parse_single(sql: str, dialect: str) -> exp.Expression:
    try:
        statements = sqlglot.parse(sql, read=dialect)
    except Exception as exc:  # sqlglot.errors.ParseError and friends
        raise SQLValidationError(f"Could not parse SQL: {exc}") from exc

    statements = [s for s in statements if s is not None]
    if len(statements) == 0:
        raise SQLValidationError("No SQL statement found.")
    if len(statements) > 1:
        raise SQLValidationError(
            "Multiple statements are not allowed; provide a single SELECT."
        )
    return statements[0]


def _check_read_only(root: exp.Expression) -> None:
    if not isinstance(root, _ALLOWED_ROOTS):
        raise SQLValidationError(
            f"Only SELECT queries are allowed (got {type(root).__name__})."
        )
    for node in root.walk():
        if isinstance(node, _FORBIDDEN_TYPES):
            raise SQLValidationError(
                f"Disallowed operation detected: {type(node).__name__}."
            )


def _check_tables(root: exp.Expression, allowed_tables: set[str]) -> None:
    # Names introduced by CTEs are allowed even though they aren't real tables.
    cte_names = {
        cte.alias_or_name.lower()
        for cte in root.find_all(exp.CTE)
        if cte.alias_or_name
    }
    allowed = {t.lower() for t in allowed_tables} | cte_names

    for table in root.find_all(exp.Table):
        name = table.name.lower()
        if name and name not in allowed:
            raise SQLValidationError(f"Query references unknown table '{table.name}'.")


def _enforce_limit(
    root: exp.Expression, max_rows: int, default_limit: int
) -> exp.Expression:
    limit_node = root.args.get("limit")
    if limit_node is None:
        return root.limit(min(default_limit, max_rows))

    # Cap an existing numeric LIMIT at max_rows. Non-literal limits get capped too.
    value: int | None = None
    expr = limit_node.expression
    if isinstance(expr, exp.Literal) and expr.is_int:
        value = int(expr.name)
    if value is None or value > max_rows:
        return root.limit(max_rows)
    return root


def validate_and_normalize(
    sql: str,
    allowed_tables: set[str],
    max_rows: int,
    default_limit: int,
    dialect: str = DEFAULT_DIALECT,
) -> str:
    """Validate ``sql`` and return a safe, LIMIT-bounded query string.

    Raises :class:`SQLValidationError` if the query is not a safe SELECT.
    """
    root = _parse_single(sql, dialect)
    _check_read_only(root)
    _check_tables(root, allowed_tables)
    root = _enforce_limit(root, max_rows=max_rows, default_limit=default_limit)
    return root.sql(dialect=dialect)
