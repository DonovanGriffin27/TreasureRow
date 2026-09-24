# backend/tests/test_admin.py
# Created by David Jackson


import os
import sys
import uuid

import pytest

# Add project root to Python path so app.py can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Add backend folder to Python path so db.py can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from db import get_connection


@pytest.fixture
def app():
    app = create_app()
    app.config.update(TESTING=True)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def set_admin_session(client):
    with client.session_transaction() as session:
        session["user"] = "admin"
        session["role"] = "admin"


def set_user_session(client):
    with client.session_transaction() as session:
        session["user"] = "student"
        session["role"] = "user"


# Tests that logged-out users cannot access the admin dashboard
def test_admin_dashboard_blocks_logged_out_users(client):
    response = client.get("/admin")
    assert response.status_code == 401


# Tests that non-admin users cannot access the admin dashboard
def test_admin_dashboard_blocks_non_admin_users(client):
    set_user_session(client)
    response = client.get("/admin")
    assert response.status_code == 403


# Tests that admins can access the admin dashboard
def test_admin_dashboard_loads_for_admin(client):
    set_admin_session(client)
    response = client.get("/admin")
    assert response.status_code == 200
    assert b"Admin Dashboard" in response.data


# Tests that the users route returns JSON for admins
def test_admin_users_route_returns_json(client, monkeypatch):
    set_admin_session(client)

    monkeypatch.setattr(
        "controllers.admin_controller.fetch_users",
        lambda: [{"id": 1, "username": "admin", "email": "admin@test.com", "role": "admin"}],
    )

    response = client.get("/admin/users")
    assert response.status_code == 200
    assert response.get_json()[0]["username"] == "admin"


# Tests that the listings route returns JSON for admins
def test_admin_listings_route_returns_json(client, monkeypatch):
    set_admin_session(client)

    monkeypatch.setattr(
        "controllers.admin_controller.fetch_listings",
        lambda: [{"id": 1, "title": "Test Hoodie", "status": "active"}],
    )

    response = client.get("/admin/listings")
    assert response.status_code == 200
    assert response.get_json()[0]["title"] == "Test Hoodie"


# Tests that the storefronts route returns JSON for admins
def test_admin_storefronts_route_returns_json(client, monkeypatch):
    set_admin_session(client)

    monkeypatch.setattr(
        "controllers.admin_controller.fetch_storefronts",
        lambda: [{"id": 1, "brand_name": "Test Brand", "owner_id": 2}],
    )

    response = client.get("/admin/storefronts")
    assert response.status_code == 200
    assert response.get_json()[0]["brand_name"] == "Test Brand"


# Tests that the real database connection works
def test_real_database_connection():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT 1")
    result = cur.fetchone()

    cur.close()
    conn.close()

    assert result[0] == 1


def create_test_user():
    unique = uuid.uuid4().hex[:8]
    username = f"test_user_{unique}"
    email = f"{username}@example.com"

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO users (username, password, email, role)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (username, "test_password", email, "user"),
    )

    user_id = cur.fetchone()[0]
    conn.commit()

    cur.close()
    conn.close()

    return user_id


def row_exists(table_name, row_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"SELECT 1 FROM {table_name} WHERE id = %s", (row_id,))
    result = cur.fetchone()

    cur.close()
    conn.close()

    return result is not None


def cleanup_user(user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()

    cur.close()
    conn.close()


# Tests that admin delete user route actually removes a user from the database
def test_admin_delete_user_in_real_database(client):
    set_admin_session(client)

    user_id = create_test_user()

    try:
        assert row_exists("users", user_id) is True

        response = client.delete(f"/admin/users/{user_id}")
        assert response.status_code == 200

        assert row_exists("users", user_id) is False

    finally:
        cleanup_user(user_id)


# Tests that logout clears the session and redirects to login
def test_logout_clears_admin_session(client):
    set_admin_session(client)

    response = client.get("/auth/logout", follow_redirects=False)

    assert response.status_code in (301, 302)
    assert "/auth/login" in response.headers["Location"]