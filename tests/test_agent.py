"""Agent tests with a fake LLM and a stubbed executor (no DB or API key)."""

import app.agent as agent_module
from app.agent import AgentError, TextToSQLAgent

SCHEMA = {
    "tables": {
        "tracks": {
            "columns": [
                {"name": "track_id", "type": "INTEGER", "nullable": False},
                {"name": "name", "type": "VARCHAR", "nullable": False},
                {"name": "genre_id", "type": "INTEGER", "nullable": True},
            ],
            "primary_key": ["track_id"],
            "foreign_keys": [],
        }
    }
}


class FakeSchemaStore:
    def get(self, refresh: bool = False):
        return SCHEMA


class FakeLLM:
    """Returns a scripted sequence of responses, one per complete() call."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def complete(self, system, messages, max_tokens=1024):
        self.calls += 1
        if not self._responses:
            return "Returned rows."  # summary fallback
        return self._responses.pop(0)


def _make_agent(llm, monkeypatch, rows=None):
    rows = rows if rows is not None else [{"name": "So What"}]
    monkeypatch.setattr(
        agent_module, "execute", lambda sql, engine, max_rows: (["name"], rows)
    )
    return TextToSQLAgent(
        llm=llm,
        schema_store=FakeSchemaStore(),
        readonly_engine=object(),
        max_retries=2,
        max_rows=100,
        default_limit=50,
    )


def test_happy_path_first_attempt(monkeypatch):
    llm = FakeLLM(["SELECT name FROM tracks", "Here are the tracks."])
    agent = _make_agent(llm, monkeypatch)
    result = agent.answer("list track names")
    assert result.attempts == 1
    assert "LIMIT 50" in result.sql.upper()
    assert result.rows == [{"name": "So What"}]
    assert result.explanation == "Here are the tracks."


def test_self_correction_after_bad_first_query(monkeypatch):
    # First response is invalid (write op) -> rejected; second is valid.
    llm = FakeLLM(
        [
            "DELETE FROM tracks",          # attempt 1: rejected by validator
            "SELECT name FROM tracks",     # attempt 2: valid
            "Summary of the tracks.",      # summary call
        ]
    )
    agent = _make_agent(llm, monkeypatch)
    result = agent.answer("list track names")
    assert result.attempts == 2
    assert result.explanation == "Summary of the tracks."


def test_gives_up_after_max_retries(monkeypatch):
    llm = FakeLLM(["DROP TABLE tracks"] * 5)
    agent = _make_agent(llm, monkeypatch)
    try:
        agent.answer("do something bad")
    except AgentError as exc:
        assert exc.attempts == 3  # 1 initial + 2 retries
        assert exc.last_sql == "DROP TABLE tracks"
    else:
        raise AssertionError("expected AgentError")
