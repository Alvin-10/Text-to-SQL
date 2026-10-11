"""SQLAlchemy engines.

Two engines, two roles:
- ``admin_engine``  : the owner role, used only for read-only catalog
  introspection.
- ``readonly_engine``: the sandboxed SELECT-only role used to run every
  generated query. It pins ``statement_timeout`` and forces the session
  read-only as defence in depth on top of the role's grants.
"""

from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

from .config import settings


def _make_admin_engine() -> Engine:
    return create_engine(settings.database_url, pool_pre_ping=True)


def _make_readonly_engine() -> Engine:
    """Read-only engine with a per-query timeout, tailored to the backend.

    - PostgreSQL: pass libpq ``options`` (``statement_timeout`` +
      forced read-only session).
    - MySQL: set ``max_execution_time`` (ms, SELECT-only) on each new
      connection. Read-only enforcement relies on the role's SELECT grants.
    """
    backend = settings.backend_name

    if backend == "postgresql":
        options = (
            f"-c statement_timeout={settings.query_timeout_ms} "
            f"-c default_transaction_read_only=on"
        )
        return create_engine(
            settings.readonly_database_url,
            pool_pre_ping=True,
            connect_args={"options": options},
        )

    engine = create_engine(settings.readonly_database_url, pool_pre_ping=True)

    if backend in ("mysql", "mariadb"):
        timeout_ms = int(settings.query_timeout_ms)

        @event.listens_for(engine, "connect")
        def _set_read_timeout(dbapi_conn, _record):  # noqa: ANN001
            cursor = dbapi_conn.cursor()
            try:
                cursor.execute(f"SET SESSION max_execution_time={timeout_ms}")
            finally:
                cursor.close()

    return engine


admin_engine: Engine = _make_admin_engine()
readonly_engine: Engine = _make_readonly_engine()
