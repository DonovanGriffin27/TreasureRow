# backend/tests/test_checkout.py
# Rewritten by Donovan Griffin - Iteration 3 to match the checkout that is
# actually built: the cart lives in the login session, the buyer enters
# name / email / contact / campus meeting location (no shipping or card
# details), and orders are looked up by confirmation number.
# (The previous version tested /api/checkout/summary and /prefill endpoints and
# a cart_items layout that no longer exist.)

import pytest

from app import create_app
from db import get_connection
from helpers import create_seller, create_user, delete_users, sign_in

BUYER_DETAILS = {
    "first_name": "Test",
    "last_name": "Buyer",
    "email": "test.buyer@my.hamptonu.edu",
    "contact": "(757) 555-0100",
    "meeting_location": "Student Center, 1st Floor",
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
    """A seller with one listing (qty 5, $15.00), a buyer, and a second buyer."""
    conn = get_connection()
    cur = conn.cursor()
    seller = create_seller(cur, "seller", quantity=5, price="15.00")
    buyer = create_user(cur, "buyer")
    other = create_user(cur, "other")
    conn.commit()
    cur.close()
    conn.close()
    yield seller, buyer, other
    delete_users([buyer["user_id"], other["user_id"], seller["user_id"]])


def _put_in_cart(client, seller, quantity):
    with client.session_transaction() as sess:
        sess["cart"] = [{
            "id": seller["listing_id"],
            "name": seller["title"],
            "price": 15.00,
            "quantity": quantity,
            "size": "M",
        }]


def _checkout(client, seller, buyer, quantity=2):
    sign_in(client, buyer)
    _put_in_cart(client, seller, quantity)
    return client.post("/api/checkout/complete", json=BUYER_DETAILS)


def test_checkout_requires_sign_in(client):
    response = client.post("/api/checkout/complete", json=BUYER_DETAILS)
    assert response.status_code == 401


def test_checkout_rejects_empty_cart(client, people):
    _, buyer, _ = people
    sign_in(client, buyer)
    response = client.post("/api/checkout/complete", json=BUYER_DETAILS)
    assert response.status_code == 400
    assert "empty" in response.get_json()["error"].lower()


def test_checkout_requires_buyer_details(client, people):
    seller, buyer, _ = people
    sign_in(client, buyer)
    _put_in_cart(client, seller, 1)
    response = client.post("/api/checkout/complete", json={"first_name": "Only"})
    assert response.status_code == 400
    assert "buyer details" in response.get_json()["error"].lower()


def test_checkout_creates_order_and_clears_cart(client, people):
    seller, buyer, _ = people
    response = _checkout(client, seller, buyer, quantity=2)
    assert response.status_code == 200, response.get_data(as_text=True)
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["confirmation_number"]
    assert float(payload["total_amount"]) == pytest.approx(30.00)
    with client.session_transaction() as sess:
        assert sess.get("cart") == []


def test_buyer_can_view_own_confirmation(client, people):
    seller, buyer, _ = people
    confirmation = _checkout(client, seller, buyer).get_json()["confirmation_number"]
    response = client.get(f"/api/orders/by-confirmation/{confirmation}")
    assert response.status_code == 200
    body = response.get_json()
    assert body["order"]["user_id"] == buyer["user_id"]
    assert len(body["order_items"]) == 1


def test_other_user_cannot_view_someone_elses_order(client, people):
    seller, buyer, other = people
    confirmation = _checkout(client, seller, buyer).get_json()["confirmation_number"]
    sign_in(client, other)
    response = client.get(f"/api/orders/by-confirmation/{confirmation}")
    assert response.status_code == 400
    assert "access denied" in response.get_json()["error"].lower()


def test_my_orders_lists_only_own_orders(client, people):
    seller, buyer, other = people
    order_id = _checkout(client, seller, buyer).get_json()["order_id"]

    response = client.get("/api/orders/my")
    assert response.status_code == 200
    assert order_id in {o["id"] for o in response.get_json()["orders"]}

    sign_in(client, other)
    response = client.get("/api/orders/my")
    assert order_id not in {o["id"] for o in response.get_json()["orders"]}


def test_checkout_rejects_more_than_in_stock(client, people):
    seller, buyer, _ = people
    response = _checkout(client, seller, buyer, quantity=99)
    assert response.status_code == 400
    assert "in stock" in response.get_json()["error"].lower()
