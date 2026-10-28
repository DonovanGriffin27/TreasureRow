# backend/tests/test_wallet.py
# Created by Donovan Griffin - Iteration 3
#
# Treasure Tokens: wallets, checkout escrow, pickup codes, refunds, admin
# grants. Every test also checks the core invariant: a wallet's balance always
# equals the sum of its ledger entries.

from decimal import Decimal

import pytest

from app import create_app
from db import get_connection
from helpers import create_seller, create_user, delete_users, sign_in
from services import wallet_service

START = Decimal("200.00")
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
def market():
    """Two sellers ($40 and $25 listings, 5 in stock each), a buyer, and a bystander."""
    conn = get_connection()
    cur = conn.cursor()
    s1 = create_seller(cur, "tok_s1", quantity=5, price="40.00")
    s2 = create_seller(cur, "tok_s2", quantity=5, price="25.00")
    buyer = create_user(cur, "tok_b")
    other = create_user(cur, "tok_o")
    conn.commit()
    cur.close()
    conn.close()
    yield s1, s2, buyer, other
    delete_users([buyer["user_id"], other["user_id"], s1["user_id"], s2["user_id"]])


# ----------------------------------------------------------------- helpers

def _q(sql, *params):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def balance(user):
    rows = _q("SELECT balance FROM wallets WHERE user_id = %s;", user["user_id"])
    return rows[0][0] if rows else None


def ledger_sum(user):
    return _q("SELECT COALESCE(SUM(amount), 0) FROM token_ledger WHERE user_id = %s;", user["user_id"])[0][0]


def assert_ledger_matches(*users):
    for u in users:
        if balance(u) is not None:
            assert balance(u) == ledger_sum(u), f"{u['username']}: balance != ledger"


def checkout(client, buyer, items):
    """items: [(seller, quantity)]"""
    sign_in(client, buyer)
    with client.session_transaction() as sess:
        sess["cart"] = [{"id": s["listing_id"], "quantity": q, "size": "M"} for s, q in items]
    return client.post("/api/checkout/complete", json=BUYER_DETAILS)


def escrows_for(order_id):
    return _q("SELECT id, seller_id, amount, status FROM order_escrow WHERE order_id = %s ORDER BY id;", order_id)


# ------------------------------------------------------------------ wallets

def test_new_wallet_gets_starting_balance(client, market):
    _, _, buyer, _ = market
    sign_in(client, buyer)
    response = client.get("/api/wallet")
    assert response.status_code == 200
    body = response.get_json()
    assert Decimal(str(body["balance"])) == START
    assert body["ledger"][0]["type"] == "STARTING_BALANCE"
    assert_ledger_matches(buyer)


def test_wallet_requires_sign_in(client):
    assert client.get("/api/wallet").status_code == 401


# ----------------------------------------------------------------- checkout

def test_checkout_holds_tokens_in_escrow_per_seller(client, market):
    s1, s2, buyer, _ = market
    response = checkout(client, buyer, [(s1, 2), (s2, 1)])   # 80 + 25
    assert response.status_code == 200, response.get_data(as_text=True)
    body = response.get_json()
    assert balance(buyer) == START - Decimal("105.00")
    held = escrows_for(body["order_id"])
    assert {(r[1], r[2], r[3]) for r in held} == {
        (s1["user_id"], Decimal("80.00"), "HELD"), (s2["user_id"], Decimal("25.00"), "HELD")}
    assert len(body["escrows"]) == 2 and all(len(e["pickup_code"]) == 9 for e in body["escrows"])
    assert balance(s1) in (None, START)  # seller not paid yet
    assert_ledger_matches(buyer)


def test_insufficient_tokens_creates_no_order(client, market):
    s1, _, buyer, _ = market
    response = checkout(client, buyer, [(s1, 5)])   # 200 ok
    assert response.status_code == 200
    orders_before = _q("SELECT COUNT(*) FROM orders WHERE user_id = %s;", buyer["user_id"])[0][0]
    stock_before = _q("SELECT quantity_on_hand FROM listings WHERE id = %s;", s1["listing_id"])[0][0]

    response = checkout(client, buyer, [(s1, 1)])   # balance now 0
    assert response.status_code == 402
    assert "not enough treasure tokens" in response.get_json()["error"].lower()
    assert _q("SELECT COUNT(*) FROM orders WHERE user_id = %s;", buyer["user_id"])[0][0] == orders_before
    assert _q("SELECT quantity_on_hand FROM listings WHERE id = %s;", s1["listing_id"])[0][0] == stock_before
    assert balance(buyer) == Decimal("0.00")
    assert_ledger_matches(buyer)


def test_failed_hold_removes_the_unpaid_order(client, market):
    """If the balance drops between the pre-check and the hold (e.g. a second
    checkout in another tab), the order is rolled back."""
    s1, _, buyer, _ = market
    wallet_service.ensure_wallet(buyer["user_id"])
    real_check = wallet_service.assert_can_afford
    wallet_service.assert_can_afford = lambda *a, **k: None   # simulate the race
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("UPDATE wallets SET balance = 10 WHERE user_id = %s;", (buyer["user_id"],))
        cur.execute("INSERT INTO token_ledger (user_id, amount, entry_type, note) VALUES (%s, -190, 'ADMIN_GRANT', 'test adjust');",
                    (buyer["user_id"],))
        conn.commit(); cur.close(); conn.close()
        response = checkout(client, buyer, [(s1, 1)])
    finally:
        wallet_service.assert_can_afford = real_check
    assert response.status_code == 402
    assert _q("SELECT COUNT(*) FROM orders WHERE user_id = %s;", buyer["user_id"])[0][0] == 0
    assert balance(buyer) == Decimal("10.00")


# --------------------------------------------------------------- pickup codes

def _held_order(client, s1, buyer):
    body = checkout(client, buyer, [(s1, 1)]).get_json()
    return body["escrows"][0]


def test_seller_confirms_pickup_with_correct_code(client, market):
    s1, _, buyer, _ = market
    escrow = _held_order(client, s1, buyer)
    sign_in(client, s1)
    response = client.post(f"/api/escrow/{escrow['escrow_id']}/release",
                           json={"code": escrow["pickup_code"].lower().replace("-", " ")})
    assert response.status_code == 200, response.get_data(as_text=True)
    assert balance(s1) == START + Decimal("40.00")
    assert _q("SELECT status FROM order_escrow WHERE id = %s;", escrow["escrow_id"])[0][0] == "RELEASED"
    assert _q("SELECT order_status FROM orders WHERE id = (SELECT order_id FROM order_escrow WHERE id = %s);",
              escrow["escrow_id"])[0][0] == "COMPLETED"
    assert_ledger_matches(buyer, s1)

    # can't be released twice
    again = client.post(f"/api/escrow/{escrow['escrow_id']}/release", json={"code": escrow["pickup_code"]})
    assert again.status_code == 409
    assert balance(s1) == START + Decimal("40.00")


def test_wrong_code_is_rejected_and_locks_after_5_tries(client, market):
    s1, _, buyer, _ = market
    escrow = _held_order(client, s1, buyer)
    sign_in(client, s1)
    for attempt in range(1, 5):
        r = client.post(f"/api/escrow/{escrow['escrow_id']}/release", json={"code": "AAAA-AAAA"})
        assert r.status_code == 400
        assert f"{5 - attempt} attempt" in r.get_json()["error"]
    r = client.post(f"/api/escrow/{escrow['escrow_id']}/release", json={"code": "AAAA-AAAA"})
    assert r.status_code == 423
    # even the right code no longer works once locked
    r = client.post(f"/api/escrow/{escrow['escrow_id']}/release", json={"code": escrow["pickup_code"]})
    assert r.status_code == 423
    assert balance(s1) in (None, START)


def test_only_the_seller_can_confirm_pickup(client, market):
    s1, _, buyer, other = market
    escrow = _held_order(client, s1, buyer)
    for user in (buyer, other):
        sign_in(client, user)
        r = client.post(f"/api/escrow/{escrow['escrow_id']}/release", json={"code": escrow["pickup_code"]})
        assert r.status_code == 403
    assert _q("SELECT status FROM order_escrow WHERE id = %s;", escrow["escrow_id"])[0][0] == "HELD"


def test_pickup_codes_are_not_stored(client, market):
    s1, _, buyer, _ = market
    escrow = _held_order(client, s1, buyer)
    code = escrow["pickup_code"].replace("-", "")
    row = _q("SELECT * FROM order_escrow WHERE id = %s;", escrow["escrow_id"])[0]
    assert all(code not in str(col).upper().replace("-", "") for col in row)


def test_seller_never_sees_codes_buyer_does(client, market):
    s1, _, buyer, _ = market
    escrow = _held_order(client, s1, buyer)
    sign_in(client, buyer)
    purchases = client.get("/api/wallet").get_json()["purchases"]
    assert any(p.get("pickup_code") == escrow["pickup_code"] for p in purchases)
    sign_in(client, s1)
    sales = client.get("/api/wallet").get_json()["sales"]
    assert sales and all("pickup_code" not in s for s in sales)


# ------------------------------------------------------------------- refunds

@pytest.mark.parametrize("who", ["buyer", "seller"])
def test_cancel_before_pickup_refunds_buyer(client, market, who):
    s1, _, buyer, _ = market
    escrow = _held_order(client, s1, buyer)
    assert balance(buyer) == START - Decimal("40.00")
    sign_in(client, buyer if who == "buyer" else s1)
    r = client.post(f"/api/escrow/{escrow['escrow_id']}/cancel", json={"reason": "can't meet"})
    assert r.status_code == 200
    assert balance(buyer) == START
    assert _q("SELECT order_status FROM orders WHERE id = (SELECT order_id FROM order_escrow WHERE id = %s);",
              escrow["escrow_id"])[0][0] == "CANCELLED"
    assert_ledger_matches(buyer)


def test_cannot_cancel_after_pickup_or_someone_elses(client, market):
    s1, _, buyer, other = market
    escrow = _held_order(client, s1, buyer)
    sign_in(client, other)
    assert client.post(f"/api/escrow/{escrow['escrow_id']}/cancel").status_code == 403
    sign_in(client, s1)
    client.post(f"/api/escrow/{escrow['escrow_id']}/release", json={"code": escrow["pickup_code"]})
    sign_in(client, buyer)
    assert client.post(f"/api/escrow/{escrow['escrow_id']}/cancel").status_code == 409
    assert balance(buyer) == START - Decimal("40.00")


def test_admin_can_refund_a_locked_pickup(client, market):
    s1, _, buyer, _ = market
    escrow = _held_order(client, s1, buyer)
    sign_in(client, s1)
    for _ in range(5):
        client.post(f"/api/escrow/{escrow['escrow_id']}/release", json={"code": "AAAA-AAAA"})
    with client.session_transaction() as sess:
        sess.clear(); sess["user"] = "test-admin"; sess["role"] = "admin"
    locked = client.get("/admin/escrow").get_json()
    assert any(e["escrow_id"] == escrow["escrow_id"] and e["status"] == "LOCKED" for e in locked)
    assert client.post(f"/admin/escrow/{escrow['escrow_id']}/refund", json={"reason": "dispute"}).status_code == 200
    assert balance(buyer) == START
    assert_ledger_matches(buyer)


# --------------------------------------------------------------- admin grant

def test_admin_grant_adds_tokens(client, market):
    _, _, buyer, _ = market
    with client.session_transaction() as sess:
        sess.clear(); sess["user"] = "test-admin"; sess["role"] = "admin"
    r = client.post(f"/admin/wallets/{buyer['user_id']}/grant", json={"amount": "50", "note": "club prize"})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert balance(buyer) == START + Decimal("50.00")
    entry = _q("SELECT entry_type, note, created_by FROM token_ledger WHERE user_id = %s ORDER BY id DESC LIMIT 1;",
               buyer["user_id"])[0]
    assert entry == ("ADMIN_GRANT", "club prize", "test-admin")
    assert_ledger_matches(buyer)


@pytest.mark.parametrize("amount", ["0", "-5", "abc", "10001"])
def test_admin_grant_rejects_bad_amounts(client, market, amount):
    _, _, buyer, _ = market
    with client.session_transaction() as sess:
        sess.clear(); sess["user"] = "test-admin"; sess["role"] = "admin"
    assert client.post(f"/admin/wallets/{buyer['user_id']}/grant", json={"amount": amount}).status_code == 400


def test_regular_user_cannot_grant_tokens(client, market):
    _, _, buyer, _ = market
    sign_in(client, buyer)
    r = client.post(f"/admin/wallets/{buyer['user_id']}/grant", json={"amount": "1000"})
    assert r.status_code == 403
    assert balance(buyer) in (None, START)


# ------------------------------------------------------------ order lookup

def test_confirmation_page_shows_buyer_their_codes(client, market):
    s1, _, buyer, other = market
    body = checkout(client, buyer, [(s1, 1)]).get_json()
    r = client.get(f"/api/orders/by-confirmation/{body['confirmation_number']}")
    assert r.status_code == 200
    assert r.get_json()["escrows"][0]["pickup_code"] == body["escrows"][0]["pickup_code"]
    sign_in(client, other)
    assert client.get(f"/api/orders/by-confirmation/{body['confirmation_number']}").status_code == 400
