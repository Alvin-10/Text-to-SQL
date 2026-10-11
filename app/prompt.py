"""Component [2]: Prompt templates.

Builds the system prompt (schema + strict rules + few-shot examples) and the
user/correction turns for the generation loop, plus the result-summary prompt.
"""

from __future__ import annotations

import re
from typing import Any

_RULES = """\
You are a careful {dialect} expert. Translate the user's question into ONE
{dialect} SELECT query.

Hard rules:
- Output SQL only. No prose, no markdown fences, no comments, no trailing
  semicolon.
- Exactly one statement, and it MUST be a SELECT (CTEs with WITH are fine).
- Never write INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, GRANT,
  COPY, or any statement that changes data or schema.
- Use only the tables and columns defined in the schema below, with their
  exact names.
- Prefer explicit JOINs using the foreign keys shown in the schema.
- Always include a reasonable LIMIT unless the query is a single aggregate.
- If the question cannot be answered from this schema, return the best
  approximate SELECT you can rather than refusing.
"""

_FEW_SHOT = """\
Examples:

Q: How many tracks are there per genre?
SQL: SELECT g.name AS genre, COUNT(*) AS track_count FROM tracks t JOIN genres g ON t.genre_id = g.genre_id GROUP BY g.name ORDER BY track_count DESC

Q: Which 5 customers have spent the most in total?
SQL: SELECT c.first_name, c.last_name, SUM(i.total) AS total_spent FROM customers c JOIN invoices i ON i.customer_id = c.customer_id GROUP BY c.customer_id, c.first_name, c.last_name ORDER BY total_spent DESC LIMIT 5

Q: List the album titles by AC/DC.
SQL: SELECT al.title FROM albums al JOIN artists ar ON al.artist_id = ar.artist_id WHERE ar.name = 'AC/DC'
"""

_FENCE_RE = re.compile(r"^```(?:sql)?\s*|\s*```$", re.IGNORECASE)


def build_system_prompt(schema_text: str, dialect_label: str = "PostgreSQL") -> str:
    rules = _RULES.format(dialect=dialect_label)
    return f"{rules}\n\nDatabase schema:\n\n{schema_text}\n\n{_FEW_SHOT}"


def build_user_prompt(question: str) -> str:
    return f"Q: {question}\nSQL:"


def build_correction_prompt(error: str) -> str:
    return (
        "That query failed with the following error:\n\n"
        f"{error}\n\n"
        "Fix the query. Return only the corrected PostgreSQL SELECT statement."
    )


def extract_sql(raw: str) -> str:
    """Strip code fences / stray labels from a model response."""
    text = raw.strip()
    # Remove surrounding ``` or ```sql fences if present.
    if text.startswith("```"):
        text = _FENCE_RE.sub("", text).strip()
    # Drop a leading "SQL:" label if the model echoed the prompt format.
    if text.lower().startswith("sql:"):
        text = text[4:].strip()
    return text.rstrip(";").strip()


def build_summary_prompt(
    question: str, sql: str, columns: list[str], rows: list[dict[str, Any]]
) -> tuple[str, str]:
    """Return (system, user) prompts for a concise NL summary of the result."""
    system = (
        "You summarise SQL query results for a non-technical reader in 1-3 "
        "sentences. Be specific and cite concrete numbers from the data. Do "
        "not mention SQL or that a query was run."
    )
    preview = rows[:10]
    user = (
        f"Question: {question}\n"
        f"SQL used: {sql}\n"
        f"Columns: {columns}\n"
        f"Rows (up to 10 shown): {preview}\n"
        f"Total rows returned: {len(rows)}\n\n"
        "Write the summary."
    )
    return system, user
