# backend/tests/test_hardening.py
# Created by Donovan Griffin - Iteration 3
#
# - CSRF: the session cookie is SameSite=Lax, and state-changing requests that
#   say they come from another website are refused.
# - Returns can only be filed for the signed-in user's own orders.
# - The app refuses to start without a SECRET_KEY.

import os

import pytest

from app import create_app
from db import get_connection
from helpers import PASSWORD, create_seller, create_user, delete_users, sign_in

BUYER_DETAILS = {
    "first_name": "Test", "last_name": "Buyer", "email": "buyer@my.hamptonu.edu",
    "contact": "(757) 555-0100", "meeting_location": "Student Center",
}


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
    seller = create_seller(cur, "hard")
    buyer = create_user(cur, "hbuyer")
    other = create_user(cur, "hother")
    conn.commit()
    cur.close()
    conn.close()
    yield seller, buyer, other
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM returns WHERE user_id = ANY(%s);", ([buyer["user_id"], other["user_id"]],))
    conn.commit()
    cur.close()
    conn.close()
    delete_users([buyer["user_id"], other["user_id"], seller["user_id"]])


def _place_order(client, seller, buyer):
    sign_in(client, buyer)
    with client.session_transaction() as sess:
        sess["cart"] = [{"id": seller["listing_id"], "quantity": 1, "size": "M"}]
    response = client.post("/api/checkout/complete", json=BUYER_DETAILS)
    assert response.status_code == 200, response.get_data(as_text=True)
    return response.get_json()["confirmation_number"]


def _file_return(client, order_number):
    return client.post("/returns", data={"order_number": order_number, "reason": "Wrong size", "has_damage": "no"})


# ------------------------------------------------------------------- CSRF

def test_session_cookie_is_samesite_lax_and_httponly(client, people):
    seller, _, _ = people
    response = client.post("/auth/login", data={"username": seller["username"], "password": PASSWORD})
    cookie = response.headers.get("Set-Cookie", "")
    assert "SameSite=Lax" in cookie
    assert "HttpOnly" in cookie


def test_cross_site_post_is_refused(client, people):
    seller, buyer, _ = people
    sign_in(client, buyer)
    response = client.post(
        "/auth/add_to_cart",
        data={"item_id": seller["listing_id"], "quantity": "1"},
        headers={"Origin": "https://evil.example"},
    )
    assert response.status_code == 403
    with client.session_transaction() as sess:
        assert not sess.get("cart")


def test_cross_site_api_delete_is_refused(client, people):
    seller, _, _ = people
    sign_in(client, seller)
    response = client.delete(f"/api/listings/{seller['listing_id']}", headers={"Origin": "https://evil.example"})
    assert response.status_code == 403


def test_same_site_post_still_works(client, people):
    seller, buyer, _ = people
    sign_in(client, buyer)
    response = client.post(
        "/auth/add_to_cart",
        data={"item_id": seller["listing_id"], "quantity": "1", "size": "M"},
        headers={"Origin": "http://localhost"},
    )
    assert response.status_code == 302


# ---------------------------------------------------------------- returns

def test_return_for_own_order_is_accepted(client, people):
    seller, buyer, _ = people
    confirmation = _place_order(client, seller, buyer)
    response = _file_return(client, confirmation)
    assert response.status_code == 201, response.get_data(as_text=True)


def test_return_for_someone_elses_order_is_rejected(client, people):
    seller, buyer, other = people
    confirmation = _place_order(client, seller, buyer)
    sign_in(client, other)
    response = _file_return(client, confirmation)
    assert response.status_code == 400
    assert "order" in response.get_json()["error"].lower()


def test_return_for_made_up_order_is_rejected(client, people):
    _, buyer, _ = people
    sign_in(client, buyer)
    response = _file_return(client, "TR-000000-NOPE00")
    assert response.status_code == 400


# ------------------------------------------------------------- secret key

def test_app_refuses_to_start_without_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app()


def test_second_return_for_same_order_is_rejected(client, people):
    """One return per order: filing it twice is refused (Ricki Davis, Iteration 3)."""
    seller, buyer, _ = people
    confirmation = _place_order(client, seller, buyer)
    assert _file_return(client, confirmation).status_code == 201
    response = _file_return(client, confirmation)
    assert response.status_code == 400
    assert "already" in response.get_json()["error"].lower()
