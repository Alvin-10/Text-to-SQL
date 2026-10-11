"""Component [1]: Schema introspection.

Reads table/column/foreign-key metadata from Postgres, caches it as JSON,
and renders a compact schema description for the LLM prompt.
"""

from __future__ import annotations

import json
import os
from typing import Any

from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from .config import settings


def introspect(engine: Engine) -> dict[str, Any]:
    """Extract a JSON-serialisable schema description from the database."""
    inspector = inspect(engine)
    tables: dict[str, Any] = {}

    # No explicit schema: use the connection's default (Postgres 'public',
    # MySQL the connected database) so this works across backends.
    for table_name in sorted(inspector.get_table_names()):
        columns = [
            {
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": bool(col["nullable"]),
            }
            for col in inspector.get_columns(table_name)
        ]
        pk = inspector.get_pk_constraint(table_name)
        fks = [
            {
                "columns": fk["constrained_columns"],
                "references_table": fk["referred_table"],
                "references_columns": fk["referred_columns"],
            }
            for fk in inspector.get_foreign_keys(table_name)
        ]
        tables[table_name] = {
            "columns": columns,
            "primary_key": pk.get("constrained_columns", []),
            "foreign_keys": fks,
        }

    return {"tables": tables}


def allowed_table_names(schema: dict[str, Any]) -> set[str]:
    """Lower-cased set of tables the validator will permit."""
    return {name.lower() for name in schema.get("tables", {})}


def render_for_prompt(schema: dict[str, Any]) -> str:
    """Render the schema as compact pseudo-DDL for the prompt context."""
    lines: list[str] = []
    for table, meta in schema.get("tables", {}).items():
        pk = set(meta.get("primary_key", []))
        col_parts = []
        for col in meta["columns"]:
            marker = " PK" if col["name"] in pk else ""
            null = "" if col["nullable"] else " NOT NULL"
            col_parts.append(f"  {col['name']} {col['type']}{null}{marker}")
        lines.append(f"TABLE {table} (")
        lines.append(",\n".join(col_parts))
        lines.append(")")
        for fk in meta.get("foreign_keys", []):
            src = ", ".join(fk["columns"])
            ref_cols = ", ".join(fk["references_columns"])
            lines.append(
                f"  FOREIGN KEY ({src}) -> {fk['references_table']}({ref_cols})"
            )
        lines.append("")
    return "\n".join(lines).strip()


class SchemaStore:
    """Introspects on demand and caches the result to disk + memory."""

    def __init__(self, engine: Engine, cache_path: str | None = None) -> None:
        self._engine = engine
        self._cache_path = cache_path or settings.schema_cache_path
        self._schema: dict[str, Any] | None = None

    def get(self, refresh: bool = False) -> dict[str, Any]:
        if self._schema is not None and not refresh:
            return self._schema
        if not refresh:
            cached = self._load_cache()
            if cached is not None:
                self._schema = cached
                return cached
        self._schema = introspect(self._engine)
        self._save_cache(self._schema)
        return self._schema

    def _load_cache(self) -> dict[str, Any] | None:
        if not os.path.exists(self._cache_path):
            return None
        try:
            with open(self._cache_path, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError):
            return None

    def _save_cache(self, schema: dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self._cache_path) or ".", exist_ok=True)
        with open(self._cache_path, "w", encoding="utf-8") as fh:
            json.dump(schema, fh, indent=2)
