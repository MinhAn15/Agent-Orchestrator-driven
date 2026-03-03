"""Tests for SQLConnector (v0.3) — uses in-memory SQLite, no external deps."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "connectors"))

import pytest
from sql_connector import SQLConnector, QueryResult


@pytest.fixture
def db():
    """Fresh in-memory SQLite connector for each test."""
    conn = SQLConnector()
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, age INTEGER)")
    return conn


class TestSQLConnector:
    def test_insert_and_select(self, db):
        db.execute("INSERT INTO users (name, age) VALUES (?, ?)", ("Alice", 30))
        rows = db.query("SELECT * FROM users")
        assert len(rows) == 1
        assert rows[0]["name"] == "Alice"
        assert rows[0]["age"] == 30

    def test_select_empty_table_returns_empty_list(self, db):
        assert db.query("SELECT * FROM users") == []

    def test_execute_many_inserts(self, db):
        data = [("Bob", 25), ("Carol", 35), ("Dave", 28)]
        db.execute_many("INSERT INTO users (name, age) VALUES (?, ?)", data)
        rows = db.query("SELECT name FROM users ORDER BY name")
        assert [r["name"] for r in rows] == ["Bob", "Carol", "Dave"]

    def test_parameterised_select(self, db):
        db.execute("INSERT INTO users (name, age) VALUES (?, ?)", ("Eve", 22))
        rows = db.query("SELECT * FROM users WHERE age > ?", (20,))
        assert len(rows) == 1
        assert rows[0]["name"] == "Eve"

    def test_query_result_first(self, db):
        db.execute("INSERT INTO users (name, age) VALUES (?, ?)", ("Frank", 40))
        result = db.execute("SELECT * FROM users")
        first = result.first()
        assert first is not None
        assert first["name"] == "Frank"

    def test_query_result_first_empty(self, db):
        result = db.execute("SELECT * FROM users")
        assert result.first() is None

    def test_query_result_scalar(self, db):
        db.execute("INSERT INTO users (name, age) VALUES (?, ?)", ("Grace", 33))
        result = db.execute("SELECT COUNT(*) AS cnt FROM users")
        assert result.scalar() == 1

    def test_query_result_len(self, db):
        db.execute_many(
            "INSERT INTO users (name, age) VALUES (?, ?)",
            [("H", 1), ("I", 2), ("J", 3)]
        )
        result = db.execute("SELECT * FROM users")
        assert len(result) == 3

    def test_update_and_verify(self, db):
        db.execute("INSERT INTO users (name, age) VALUES (?, ?)", ("Kate", 20))
        db.execute("UPDATE users SET age = ? WHERE name = ?", (21, "Kate"))
        rows = db.query("SELECT age FROM users WHERE name = ?", ("Kate",))
        assert rows[0]["age"] == 21

    def test_delete_and_verify(self, db):
        db.execute("INSERT INTO users (name, age) VALUES (?, ?)", ("Leo", 45))
        db.execute("DELETE FROM users WHERE name = ?", ("Leo",))
        assert db.query("SELECT * FROM users") == []

    def test_context_manager(self):
        with SQLConnector() as conn:
            conn.execute("CREATE TABLE t (x INTEGER)")
            conn.execute("INSERT INTO t VALUES (?)", (42,))
            rows = conn.query("SELECT * FROM t")
            assert rows[0]["x"] == 42
