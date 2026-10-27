# backend/tests/test_ownership.py
# Created by Donovan Griffin - Iteration 3
#
# Regression tests for the listing/storefront ownership bug (Project Plan 1.3):
# one signed-in account must never be able to change or delete another
# account's storefront or listings - not by switching accounts in the same
# browser, not by calling the API directly, and not by sending spoofed
# X-User-Id / X-User-Role headers (which the API used to trust).
#
# Runs against the local TEST database only (see conftest.py).

import pytest

from app import create_app
from db import get_connection
from helpers import PASSWORD, create_seller, delete_users, sign_in


# ---------------------------------------------------------------- fixtures

@pytest.fixture(scope="module")
def app():
    app = create_app()
    app.config.update(TESTING=True)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def sellers():
    """Two independent sellers (A and B), removed again after each test."""
    conn = get_connection()
    cur = conn.cursor()
    a = create_seller(cur, "a")
    b = create_seller(cur, "b")
    conn.commit()
    cur.close()
    conn.close()
    yield a, b
    delete_users([a["user_id"], b["user_id"]])


def _sign_in_as(client, seller):
    sign_in(client, seller)


def _listing(listing_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT title, status FROM listings WHERE id = %s;", (listing_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return {"title": row[0], "status": row[1]}


def _storefront(storefront_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT bio, is_active FROM storefronts WHERE id = %s;", (storefront_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return {"bio": row[0], "is_active": row[1]}


# ------------------------------------------------------- signed-out access

def test_signed_out_api_requests_are_rejected(client, sellers):
    a, _ = sellers
    assert client.put(f"/api/listings/{a['listing_id']}", json={"title": "x"}).status_code == 401
    assert client.delete(f"/api/listings/{a['listing_id']}").status_code == 401
    assert client.put(f"/api/storefronts/{a['storefront_id']}", json={"bio": "x"}).status_code == 401
    assert _listing(a["listing_id"]) == {"title": a["title"], "status": "ACTIVE"}
    assert _storefront(a["storefront_id"])["bio"] == a["bio"]


def test_spoofed_headers_without_a_session_are_rejected(client, sellers):
    a, _ = sellers
    spoof = {"X-User-Id": str(a["user_id"]), "X-User-Role": "admin"}
    assert client.put(f"/api/listings/{a['listing_id']}", json={"title": "x"}, headers=spoof).status_code == 401
    assert client.delete(f"/api/listings/{a['listing_id']}", headers=spoof).status_code == 401
    assert _listing(a["listing_id"])["status"] == "ACTIVE"


# ------------------------------------------------- owner can manage own data

def test_owner_can_update_own_listing(client, sellers):
    a, _ = sellers
    _sign_in_as(client, a)
    response = client.put(f"/api/listings/{a['listing_id']}", json={"title": "Renamed by owner"})
    assert response.status_code == 200
    assert _listing(a["listing_id"])["title"] == "Renamed by owner"


def test_owner_can_update_own_storefront(client, sellers):
    a, _ = sellers
    _sign_in_as(client, a)
    response = client.put(f"/api/storefronts/{a['storefront_id']}", json={"bio": "Updated by owner"})
    assert response.status_code == 200
    assert _storefront(a["storefront_id"])["bio"] == "Updated by owner"


# ------------------------------------ another account cannot touch A's data

def test_other_user_cannot_update_listing(client, sellers):
    a, b = sellers
    _sign_in_as(client, b)
    response = client.put(f"/api/listings/{a['listing_id']}", json={"title": "Hijacked"})
    assert response.status_code == 403
    assert _listing(a["listing_id"])["title"] == a["title"]


def test_other_user_cannot_delete_listing(client, sellers):
    a, b = sellers
    _sign_in_as(client, b)
    assert client.delete(f"/api/listings/{a['listing_id']}").status_code == 403
    assert client.patch(f"/api/listings/{a['listing_id']}/deactivate").status_code == 403
    assert _listing(a["listing_id"])["status"] == "ACTIVE"


def test_other_user_cannot_update_or_deactivate_storefront(client, sellers):
    a, b = sellers
    _sign_in_as(client, b)
    assert client.put(f"/api/storefronts/{a['storefront_id']}", json={"bio": "Hijacked"}).status_code == 403
    assert client.patch(f"/api/storefronts/{a['storefront_id']}/deactivate").status_code == 403
    assert _storefront(a["storefront_id"]) == {"bio": a["bio"], "is_active": True}


def test_spoofed_identity_headers_are_ignored(client, sellers):
    """Signed in as B but claiming to be A (and an admin) via headers."""
    a, b = sellers
    _sign_in_as(client, b)
    spoof = {"X-User-Id": str(a["user_id"]), "X-User-Role": "admin"}
    assert client.put(f"/api/listings/{a['listing_id']}", json={"title": "Hijacked"}, headers=spoof).status_code == 403
    assert client.delete(f"/api/listings/{a['listing_id']}", headers=spoof).status_code == 403
    assert client.put(f"/api/storefronts/{a['storefront_id']}", json={"bio": "Hijacked"}, headers=spoof).status_code == 403
    assert _listing(a["listing_id"]) == {"title": a["title"], "status": "ACTIVE"}
    assert _storefront(a["storefront_id"])["bio"] == a["bio"]


def test_my_listings_only_returns_own_listings(client, sellers):
    a, b = sellers
    _sign_in_as(client, b)
    response = client.get("/api/listings/my", headers={"X-User-Id": str(a["user_id"])})
    assert response.status_code == 200
    ids = {item["id"] for item in response.get_json()}
    assert b["listing_id"] in ids
    assert a["listing_id"] not in ids


# ------------------------------------------- account switching, same browser

def test_account_switching_in_same_browser(client, sellers):
    """Original bug: sign in as A, then as B in the same browser, and B could
    still act on A's data. Uses the real login form both times."""
    a, b = sellers
    assert client.post("/auth/login", data={"username": a["username"], "password": PASSWORD}).status_code == 302
    assert client.get("/auth/api/auth/me").get_json()["id"] == a["user_id"]

    assert client.post("/auth/login", data={"username": b["username"], "password": PASSWORD}).status_code == 302
    assert client.get("/auth/api/auth/me").get_json()["id"] == b["user_id"]

    assert client.put(f"/api/listings/{a['listing_id']}", json={"title": "Hijacked"}).status_code == 403
    assert client.delete(f"/api/listings/{a['listing_id']}").status_code == 403
    assert _listing(a["listing_id"]) == {"title": a["title"], "status": "ACTIVE"}


def test_logout_ends_access(client, sellers):
    a, _ = sellers
    client.post("/auth/login", data={"username": a["username"], "password": PASSWORD})
    client.get("/auth/logout")
    assert client.put(f"/api/listings/{a['listing_id']}", json={"title": "x"}).status_code == 401
    assert client.get("/auth/api/auth/me").status_code == 401


# ------------------------------------------------------------------- admin

def test_admin_can_manage_any_listing(client, sellers):
    a, _ = sellers
    with client.session_transaction() as sess:
        sess.clear()
        sess["user"] = "test-admin"
        sess["role"] = "admin"
    response = client.put(f"/api/listings/{a['listing_id']}", json={"title": "Edited by admin"})
    assert response.status_code == 200
    assert _listing(a["listing_id"])["title"] == "Edited by admin"


def test_regular_user_cannot_use_admin_api(client, sellers):
    _, b = sellers
    _sign_in_as(client, b)
    assert client.get("/admin/users").status_code == 403
    assert client.delete(f"/admin/listings/{b['listing_id']}").status_code == 403
