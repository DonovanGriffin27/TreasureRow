# Updated by Donovan Griffin - Iteration 3: the original test printed the result
# but asserted nothing (it passed even when registration failed) and reused the
# fixed username "ahw", so every run after the first silently failed. These
# tests assert the outcome, use unique users, and clean up after themselves.

import uuid

import pytest

from config.db import get_connection
from helpers import delete_users
from services.auth_services import AuthService


@pytest.fixture
def conn():
    conn = get_connection()
    assert conn is not None, "test database is not reachable"
    yield conn
    conn.close()


@pytest.fixture
def new_username(conn):
    username = f"t_reg_{uuid.uuid4().hex[:8]}"
    yield username
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = %s;", (username,))
    row = cur.fetchone()
    cur.close()
    delete_users([row[0]] if row else [])


def _stored_password(conn, username):
    cur = conn.cursor()
    cur.execute("SELECT password FROM users WHERE username = %s;", (username,))
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None


def test_registration(conn, new_username):
    success, message = AuthService().register_user(
        username=new_username, password="SecurePassword123",
        email=f"{new_username}@my.hamptonu.edu", db_conn=conn,
    )
    assert success, message
    stored = _stored_password(conn, new_username)
    assert stored is not None
    assert stored != "SecurePassword123"  # stored as a hash, never plaintext


def test_registered_user_can_log_in(conn, new_username):
    auth = AuthService()
    auth.register_user(new_username, "SecurePassword123", f"{new_username}@hamptonu.edu", conn)
    assert auth.validate_login(new_username, "SecurePassword123", conn) == (True, "user")
    assert auth.validate_login(new_username, "wrong-password", conn) == (False, None)


def test_duplicate_username_is_rejected(conn, new_username):
    auth = AuthService()
    assert auth.register_user(new_username, "pw-123456", f"{new_username}@hamptonu.edu", conn)[0]
    success, _ = auth.register_user(new_username, "pw-123456", f"{new_username}2@hamptonu.edu", conn)
    assert not success


@pytest.mark.parametrize("email", [
    "student@gmail.com",
    "student@fakehamptonu.edu",   # look-alike domain
    "hamptonu.edu",               # no @ at all
])
def test_non_hampton_email_is_rejected(conn, new_username, email):
    success, message = AuthService().register_user(new_username, "pw-123456", email, conn)
    assert not success
    assert "hampton" in message.lower()
    assert _stored_password(conn, new_username) is None
