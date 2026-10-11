"""Unit tests for the SQL validator (no database or LLM required)."""

import pytest

from app.prompt import extract_sql
from app.validator import SQLValidationError, validate_and_normalize

ALLOWED = {"tracks", "albums", "artists", "genres", "invoices", "customers"}


def _validate(sql, max_rows=100, default_limit=50):
    return validate_and_normalize(
        sql, allowed_tables=ALLOWED, max_rows=max_rows, default_limit=default_limit
    )


# --- accepted queries -------------------------------------------------------

def test_simple_select_gets_default_limit():
    out = _validate("SELECT name FROM tracks")
    assert "LIMIT 50" in out.upper()


def test_existing_limit_below_cap_is_kept():
    out = _validate("SELECT name FROM tracks LIMIT 10")
    assert "LIMIT 10" in out.upper()


def test_existing_limit_above_cap_is_capped():
    out = _validate("SELECT name FROM tracks LIMIT 9999", max_rows=100)
    assert "LIMIT 100" in out.upper()
    assert "9999" not in out


def test_join_across_allowed_tables_ok():
    sql = (
        "SELECT ar.name, COUNT(*) FROM tracks t "
        "JOIN albums al ON t.album_id = al.album_id "
        "JOIN artists ar ON al.artist_id = ar.artist_id GROUP BY ar.name"
    )
    assert "GROUP BY" in _validate(sql).upper()


def test_cte_names_are_allowed():
    sql = (
        "WITH top AS (SELECT genre_id, COUNT(*) c FROM tracks GROUP BY genre_id) "
        "SELECT * FROM top ORDER BY c DESC"
    )
    assert _validate(sql)  # does not raise


# --- rejected queries -------------------------------------------------------

@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO tracks (name) VALUES ('x')",
        "UPDATE tracks SET name = 'x'",
        "DELETE FROM tracks",
        "DROP TABLE tracks",
        "ALTER TABLE tracks ADD COLUMN c INT",
        "TRUNCATE tracks",
        "CREATE TABLE evil (id int)",
        "GRANT SELECT ON tracks TO public",
    ],
)
def test_non_select_is_rejected(sql):
    with pytest.raises(SQLValidationError):
        _validate(sql)


def test_multiple_statements_rejected():
    with pytest.raises(SQLValidationError):
        _validate("SELECT 1 FROM tracks; DROP TABLE tracks")


def test_unknown_table_rejected():
    with pytest.raises(SQLValidationError):
        _validate("SELECT * FROM secret_users")


def test_garbage_rejected():
    with pytest.raises(SQLValidationError):
        _validate("this is not sql")


def test_subquery_touching_unknown_table_rejected():
    with pytest.raises(SQLValidationError):
        _validate(
            "SELECT name FROM tracks WHERE album_id IN "
            "(SELECT id FROM pg_authid)"
        )


# --- extract_sql helper -----------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("SELECT 1", "SELECT 1"),
        ("```sql\nSELECT 1\n```", "SELECT 1"),
        ("```\nSELECT 1\n```", "SELECT 1"),
        ("SQL: SELECT 1", "SELECT 1"),
        ("SELECT 1;", "SELECT 1"),
    ],
)
def test_extract_sql(raw, expected):
    assert extract_sql(raw) == expected
