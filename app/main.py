"""Component [6]: API layer.

POST /query      -> {sql, columns, results, explanation, row_count, attempts}
GET  /schema     -> cached schema JSON
POST /schema/refresh -> re-introspect the database
GET  /health     -> liveness
"""

from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from .agent import AgentError, TextToSQLAgent
from .config import settings
from .db import admin_engine, readonly_engine
from .llm import LLMError, get_llm
from .models import QueryRequest, QueryResponse
from .schema_introspector import SchemaStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("text2sql")

app = FastAPI(title="Text-to-SQL Agent", version="1.0.0")

schema_store = SchemaStore(admin_engine)
_agent: TextToSQLAgent | None = None


def get_agent() -> TextToSQLAgent:
    """Build the agent lazily so the app can start without an LLM key."""
    global _agent
    if _agent is None:
        try:
            llm = get_llm()
        except LLMError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        _agent = TextToSQLAgent(
            llm=llm,
            schema_store=schema_store,
            readonly_engine=readonly_engine,
            max_retries=settings.max_retries,
            max_rows=settings.max_rows,
            default_limit=settings.default_limit,
            dialect=settings.sql_dialect,
            dialect_label=settings.sql_dialect_label,
        )
    return _agent


@app.on_event("startup")
def _warm_schema() -> None:
    try:
        schema_store.get(refresh=True)
        logger.info("Schema cache warmed.")
    except Exception as exc:  # DB may not be up yet; introspect on first use.
        logger.warning("Could not warm schema cache at startup: %s", exc)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/schema")
def get_schema() -> dict:
    try:
        return schema_store.get()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")


@app.post("/schema/refresh")
def refresh_schema() -> dict:
    try:
        return schema_store.get(refresh=True)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest, agent: TextToSQLAgent = Depends(get_agent)) -> QueryResponse:
    try:
        result = agent.answer(req.question)
    except AgentError as exc:
        return JSONResponse(
            status_code=422,
            content={
                "detail": str(exc),
                "attempts": exc.attempts,
                "last_sql": exc.last_sql,
            },
        )
    except SQLAlchemyError as exc:
        # e.g. the database is unreachable during schema introspection.
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {getattr(exc, 'orig', exc)}",
        ) from exc

    return QueryResponse(
        sql=result.sql,
        columns=result.columns,
        results=result.rows,
        explanation=result.explanation,
        row_count=len(result.rows),
        attempts=result.attempts,
    )
