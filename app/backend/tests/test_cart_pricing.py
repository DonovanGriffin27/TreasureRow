# backend/tests/test_cart_pricing.py
# Created by Donovan Griffin - Iteration 3
#
# Add-to-cart used to take the item's price and name from the submitted form,
# and checkout totalled the order from those cart prices - so anyone could
# edit the form and buy a $40 item for $0.01. These tests send tampered
# values and check the server uses the real listing data instead.

import pytest

from app import create_app
from db import get_connection
from helpers import create_seller, create_user, delete_users, sign_in

REAL_PRICE = 40.00
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
def shop():
    """A seller with a $40.00 listing (qty 5) and a signed-in buyer."""
    conn = get_connection()
    cur = conn.cursor()
    seller = create_seller(cur, "price", quantity=5, price=f"{REAL_PRICE:.2f}")
    buyer = create_user(cur, "pbuyer")
    conn.commit()
    cur.close()
    conn.close()
    yield seller, buyer
    delete_users([buyer["user_id"], seller["user_id"]])


def _add(client, listing_id, **form):
    data = {"item_id": str(listing_id), "item_name": "Fake name", "price": "0.01",
            "quantity": "1", "size": "M"}
    data.update(form)
    return client.post("/auth/add_to_cart", data=data)


def _cart(client):
    with client.session_transaction() as sess:
        return list(sess.get("cart", []))


def _set_listing(listing_id, **fields):
    conn = get_connection()
    cur = conn.cursor()
    for column, value in fields.items():
        cur.execute(f"UPDATE listings SET {column} = %s WHERE id = %s;", (value, listing_id))
    conn.commit()
    cur.close()
    conn.close()


def test_tampered_price_and_name_are_ignored(client, shop):
    seller, buyer = shop
    sign_in(client, buyer)
    response = _add(client, seller["listing_id"], price="0.01", item_name="<b>Free stuff</b>")
    assert response.status_code == 302  # back to the bag
    cart = _cart(client)
    assert len(cart) == 1
    assert cart[0]["price"] == pytest.approx(REAL_PRICE)
    assert cart[0]["name"] == seller["title"]


@pytest.mark.parametrize("quantity", ["-3", "0", "abc", "1.5"])
def test_invalid_quantity_is_rejected(client, shop, quantity):
    seller, buyer = shop
    sign_in(client, buyer)
    response = _add(client, seller["listing_id"], quantity=quantity)
    assert response.status_code == 400
    assert _cart(client) == []


def test_quantity_above_stock_is_rejected(client, shop):
    seller, buyer = shop
    sign_in(client, buyer)
    response = _add(client, seller["listing_id"], quantity="6")  # only 5 in stock
    assert response.status_code == 409
    assert _cart(client) == []


def test_unknown_listing_is_rejected(client, shop):
    _, buyer = shop
    sign_in(client, buyer)
    assert _add(client, 999999999).status_code == 404
    assert _add(client, "not-a-number").status_code == 404
    assert _cart(client) == []


@pytest.mark.parametrize("status", ["DELETED", "INACTIVE", "SOLD_OUT"])
def test_unavailable_listing_is_rejected(client, shop, status):
    seller, buyer = shop
    _set_listing(seller["listing_id"], status=status)
    sign_in(client, buyer)
    assert _add(client, seller["listing_id"]).status_code in (404, 409)
    assert _cart(client) == []


def test_checkout_charges_the_real_price_for_a_tampered_cart(client, shop):
    """A cart saved before this fix (or edited) still holds a fake price;
    checkout must re-price every item from the database."""
    seller, buyer = shop
    sign_in(client, buyer)
    with client.session_transaction() as sess:
        sess["cart"] = [{"id": seller["listing_id"], "name": "Fake", "price": 0.01,
                         "quantity": 2, "size": "M"}]
    response = client.post("/api/checkout/complete", json=BUYER_DETAILS)
    assert response.status_code == 200, response.get_data(as_text=True)
    assert float(response.get_json()["total_amount"]) == pytest.approx(2 * REAL_PRICE)


def test_checkout_rejects_cart_items_without_a_listing(client, shop):
    _, buyer = shop
    sign_in(client, buyer)
    with client.session_transaction() as sess:
        sess["cart"] = [{"name": "Made-up item", "price": 0.01, "quantity": 1, "size": "M"}]
    response = client.post("/api/checkout/complete", json=BUYER_DETAILS)
    assert response.status_code == 400
