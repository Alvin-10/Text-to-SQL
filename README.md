# Text-to-SQL Agent with Safety Guardrails

Natural-language questions → validated, read-only SQL → results + a plain-English
summary. Built around a hard safety boundary: every generated query is parsed and
checked with `sqlglot` **and** run through a SELECT-only Postgres role with a query
timeout.

```
User (NL query) → FastAPI /query → Agent Orchestrator
                                       ↓
                     [1] Schema Introspector   (reads schema, caches JSON)
                     [2] SQL Generator         (Gemini + schema + few-shot)
                     [3] Validator / Sandbox   (sqlglot: SELECT-only? known tables? LIMIT?)
                     [4] Executor              (read-only role + statement_timeout)
                     [5] Self-Correction Loop  (feed errors back to the LLM, ≤ N retries)
                                       ↓
                     Result → {sql, columns, results, explanation}
```

## Tech stack

FastAPI · PostgreSQL · SQLAlchemy · sqlglot · Google Gemini (`gemini-2.5-flash`).
Seed data is a Chinook-style digital-media store (artists → albums → tracks, sold
via invoices).

## Layout

| Path | Component |
|------|-----------|
| `app/schema_introspector.py` | [1] introspection + JSON cache + prompt rendering |
| `app/prompt.py`              | [2] system prompt, few-shot examples, correction turns |
| `app/validator.py`           | [3] sqlglot validation + LIMIT enforcement |
| `app/executor.py`            | [4] sandboxed execution + row cap + serialisation |
| `app/agent.py`               | [5] orchestrator + self-correction loop |
| `app/main.py`                | [6] FastAPI endpoints |
| `seed/`                      | schema + seed data + read-only role |

## Setup

### 1. Start Postgres (Docker)

```bash
docker compose up -d
```

This boots Postgres 16, loads the Chinook-style schema and data, and creates the
`readonly` role. Data is seeded only on first init (fresh volume); to reseed:
`docker compose down -v && docker compose up -d`.

#### Alternative: use an existing MySQL server (no Docker)

The app is dialect-agnostic — the SQL dialect is auto-detected from the DB URL.
To use MySQL 8 instead of Postgres, load the MySQL seed and point `.env` at it:

```sql
-- in MySQL Workbench (or the mysql CLI), as an admin user:
CREATE DATABASE chinook;
USE chinook;
SOURCE seed/mysql_chinook.sql;    -- schema + data
SOURCE seed/mysql_readonly.sql;   -- creates the read-only user
```

Then set both URLs in `.env` to the `mysql+pymysql://…` form (see `.env.example`).
Everything else — validator, executor, retry loop — works unchanged; the read-only
user + `max_execution_time` timeout replace the Postgres role + `statement_timeout`.

### 2. Configure the app

```bash
# Copy .env.example to .env (PowerShell: Copy-Item .env.example .env)
# Then replace the placeholder GEMINI_API_KEY value in .env.
```

Get a key in [Google AI Studio](https://aistudio.google.com/app/apikey): sign in,
create an API key, then paste it as the value of `GEMINI_API_KEY` in `.env`.
Keep the key private and do not commit `.env`. Gemini quotas, model availability,
and pricing can change; check Google AI Studio and the Gemini API pricing page
for current details.

### 3. Install and run

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate     |  macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

## Use it

```bash
curl -s localhost:8000/query \
  -H 'content-type: application/json' \
  -d '{"question": "Which 5 customers have spent the most in total?"}'
```

```json
{
  "sql": "SELECT c.first_name, c.last_name, SUM(i.total) AS total_spent FROM ... LIMIT 5",
  "columns": ["first_name", "last_name", "total_spent"],
  "results": [{"first_name": "Helena", "last_name": "Holý", "total_spent": 13.86}],
  "explanation": "Helena Holý is the top spender at $13.86, followed by ...",
  "row_count": 5,
  "attempts": 1
}
```

Other endpoints:

- `GET  /health` — liveness
- `GET  /schema` — cached schema JSON (what the LLM sees)
- `POST /schema/refresh` — re-introspect the database
- Interactive docs at `http://localhost:8000/docs`

## Safety guardrails

1. **Prompt** insists on a single read-only SELECT with exact column names.
2. **Validator** (`sqlglot`) rejects anything that isn't one SELECT statement,
   any write/DDL/command (`INSERT`, `UPDATE`, `DROP`, `GRANT`, …), any reference to
   an unknown table, and injects/caps a `LIMIT`.
3. **Read-only role** — the executor connects as `readonly` (SELECT grants only),
   with the session forced read-only and a `statement_timeout`.
4. **Row cap** — at most `MAX_ROWS` rows are read back.

The validator and the DB role are independent; a query must pass both.

## Configuration (`.env`)

| Var | Default | Meaning |
|-----|---------|---------|
| `LLM_PROVIDER` | `gemini` | LLM provider |
| `LLM_MODEL` | `gemini-2.5-flash` | Gemini model |
| `GEMINI_API_KEY` | — | API key from Google AI Studio |
| `MAX_RETRIES` | `2` | self-correction attempts after the first try |
| `QUERY_TIMEOUT_MS` | `5000` | per-query statement timeout |
| `MAX_ROWS` | `100` | hard cap on returned rows |
| `DEFAULT_LIMIT` | `100` | LIMIT injected when the query has none |

## Tests

```bash
pytest
```

`tests/test_validator.py` and `tests/test_agent.py` run without a database or API
key (the agent test uses a fake LLM and a stubbed executor).
