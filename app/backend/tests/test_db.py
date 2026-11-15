# backend/tests/test_db.py
# Rewritten by Jonah Goodwine - Iteration 4
# Was a script that connected to the database when pytest imported it and
# printed a message instead of asserting anything. Now it's a real test.

from db import get_connection


def test_database_connection():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1")
    result = cur.fetchone()
    cur.close()
    conn.close()
    assert result[0] == 1
