# backend/tests/test_security_headers_and_messages.py
# Created by Donovan Griffin - Iteration 3
#
# Covers the SCRUM-61 security hardening and buyer/seller messaging:
# - every response carries the security headers
# - the app refuses a placeholder SECRET_KEY
# - signup username / password length rules
# - a failed login closes its database connection
# - confirmation numbers are TR-YYMMDD-XXXXXX and not repeated
# - messages: sign-in required, input checks, only the two people in a
#   conversation can read it, and reading marks it read

import re
import uuid

import pytest

from app import create_app
from config.db import get_connection
from helpers import create_seller, create_user, delete_users, sign_in
from services.auth_services import AuthService
from services.checkout_service import _generate_confirmation_number


@pytest.fixture(scope="module")
def app():
    app = create_app()
    app.config.update(TESTING=True)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def people():
    conn = get_connection()
    cur = conn.cursor()
    seller = create_seller(cur, "msgseller")
    buyer = create_user(cur, "msgbuyer")
    other = create_user(cur, "msgother")
    conn.commit()
    cur.close()
    conn.close()
    yield seller, buyer, other
    delete_users([buyer["user_id"], other["user_id"], seller["user_id"]])  # messages cascade


# --------------------------------------------------------- security headers

@pytest.mark.parametrize("path", ["/", "/auth/login", "/api/messages"])
def test_security_headers_on_every_response(client, path):
    response = client.get(path)
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


@pytest.mark.parametrize("value", ["change-me", "CHANGEME", "dev-secret", "  secret  "])
def test_app_refuses_placeholder_secret_key(monkeypatch, value):
    monkeypatch.setenv("SECRET_KEY", value)
    with pytest.raises(RuntimeError, match="placeholder"):
        create_app()


# ------------------------------------------------------- signup length rules

@pytest.fixture
def db_conn():
    conn = get_connection()
    yield conn
    conn.close()


@pytest.mark.parametrize("username, password, error", [
    ("ab", "SecurePassword123", "Username"),
    ("u" * 51, "SecurePassword123", "Username"),
    (None, "short7!", "Password"),
    (None, "p" * 129, "Password"),
])
def test_signup_length_rules(db_conn, username, password, error):
    username = username or f"t_len_{uuid.uuid4().hex[:8]}"
    success, message = AuthService().register_user(username, password, f"{username[:40]}@hamptonu.edu", db_conn)
    assert not success
    assert error in message
    cur = db_conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE username = %s;", (username,))
    assert cur.fetchone()[0] == 0
    cur.close()


def test_failed_login_closes_its_connection(client, monkeypatch):
    import controllers.auth_controller as auth_controller
    opened = []

    def tracking_connection():
        conn = get_connection()
        opened.append(conn)
        return conn

    monkeypatch.setattr(auth_controller, "get_connection", tracking_connection)
    for _ in range(5):
        response = client.post("/auth/login", data={"username": "nobody_here", "password": "wrong-pass"})
        assert response.status_code == 401
    assert len(opened) == 5
    assert all(conn.closed for conn in opened)


# ----------------------------------------------------- confirmation numbers

def test_confirmation_numbers_are_tr_format_and_unique():
    numbers = {_generate_confirmation_number() for _ in range(500)}
    assert len(numbers) == 500
    assert all(re.fullmatch(r"TR-\d{6}-[A-Z0-9]{6}", n) for n in numbers)


# ------------------------------------------------------------------ messages

def test_messages_require_sign_in(client):
    assert client.get("/api/messages").status_code in (401, 403)
    assert client.post("/api/messages", json={"receiver_id": 1, "body": "hi"}).status_code in (401, 403)


def test_buyer_and_seller_can_message_about_a_listing(client, people):
    seller, buyer, _ = people
    sign_in(client, buyer)
    response = client.post("/api/messages", json={
        "receiver_id": seller["user_id"], "listing_id": seller["listing_id"], "body": "Is this still available?"})
    assert response.status_code == 201, response.get_data(as_text=True)

    sign_in(client, seller)
    convos = client.get("/api/messages").get_json()
    convo = next(c for c in convos if c["other_id"] == buyer["user_id"])
    assert convo["listing_id"] == seller["listing_id"]
    assert convo["unread"] == 1

    thread = client.get(f"/api/messages/{buyer['user_id']}?listing={seller['listing_id']}").get_json()
    assert [m["body"] for m in thread["messages"]] == ["Is this still available?"]
    convos = client.get("/api/messages").get_json()
    assert next(c for c in convos if c["other_id"] == buyer["user_id"])["unread"] == 0  # reading marks it read


def test_other_users_cannot_see_a_conversation(client, people):
    seller, buyer, other = people
    sign_in(client, buyer)
    client.post("/api/messages", json={"receiver_id": seller["user_id"], "body": "private note"})

    sign_in(client, other)
    assert all(c["other_id"] not in (buyer["user_id"], seller["user_id"]) for c in client.get("/api/messages").get_json())
    thread = client.get(f"/api/messages/{seller['user_id']}").get_json()
    assert thread["messages"] == []


@pytest.mark.parametrize("payload, status", [
    ({"body": ""}, 400),                       # empty
    ({"body": "x" * 1001}, 400),               # over 1000 characters
    ({"body": "hi", "receiver_id": "abc"}, 400),
    ({"body": "hi", "receiver_id": 999999999}, 404),
    ({"body": "hi", "listing_id": 999999999}, 404),
])
def test_bad_messages_are_rejected(client, people, payload, status):
    seller, buyer, _ = people
    sign_in(client, buyer)
    body = {"receiver_id": seller["user_id"], **payload}
    assert client.post("/api/messages", json=body).status_code == status


def test_cannot_message_yourself(client, people):
    _, buyer, _ = people
    sign_in(client, buyer)
    response = client.post("/api/messages", json={"receiver_id": buyer["user_id"], "body": "hi me"})
    assert response.status_code == 400
