"""
wallet_service.py

Treasure Row Campus Marketplace
Created by Donovan Griffin - Iteration 3

Business rules for the Treasure Tokens (TT) payment system.

  * 1 TT = $1.00 of listing price. No real money or card data is involved.
  * Every user has a wallet, opened automatically with a starting balance.
  * Checkout moves the order total from the buyer's wallet into escrow, one
    escrow per seller in the order.
  * Each escrow has a one-time pickup code only the buyer can see. At the
    meetup the seller enters it; the tokens are then released to the seller.
  * Before pickup the buyer, the seller, or an admin can cancel: the buyer is
    refunded.
  * Every balance change is written to token_ledger in the same database
    transaction, so a wallet's balance always equals the sum of its ledger.

Pickup codes are never stored. Each escrow stores a random nonce, and the
code is HMAC-SHA256(SECRET_KEY, "<escrow id>:<nonce>"), so a copy of the
database alone does not reveal any code.
"""

import hashlib
import hmac
import os
import secrets
from decimal import Decimal, InvalidOperation

from db import get_connection
from models import wallet_model as wm

TOKEN_UNIT = "TT"
MAX_CODE_ATTEMPTS = 5
MAX_ADMIN_GRANT = Decimal("10000")


class TokenError(Exception):
    """A token operation was refused; status is the HTTP status the API should return."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def starting_balance():
    try:
        return Decimal(os.getenv("TOKEN_STARTING_BALANCE", "200")).quantize(Decimal("0.01"))
    except InvalidOperation:
        return Decimal("200.00")


def _money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"))


# ---------------------------------------------------------------- pickup codes

# No look-alike characters (no I/L/1, O/0, U/V), so codes can be read aloud at a meetup.
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTWXYZ23456789"


def pickup_code(escrow_id, nonce):
    """The 8-character pickup code for an escrow, formatted XXXX-XXXX."""
    key = (os.getenv("SECRET_KEY") or "").encode()
    digest = hmac.new(key, f"{escrow_id}:{nonce}".encode(), hashlib.sha256).digest()
    raw = "".join(CODE_ALPHABET[b % len(CODE_ALPHABET)] for b in digest[:8])
    return f"{raw[:4]}-{raw[4:]}"


def _normalize_code(code):
    return "".join(ch for ch in str(code or "").upper() if ch.isalnum())


def _code_matches(escrow, entered):
    expected = _normalize_code(pickup_code(escrow["id"], escrow["code_nonce"]))
    return hmac.compare_digest(expected, _normalize_code(entered))


# --------------------------------------------------------------------- wallets

def ensure_wallet(user_id, cur=None):
    """Open the user's wallet (with the starting balance) if they don't have one yet."""
    own = cur is None
    conn = None
    if own:
        conn = get_connection()
        cur = conn.cursor()
    try:
        amount = starting_balance()
        if wm.insert_wallet_if_missing(cur, user_id, amount) and amount > 0:
            wm.add_ledger_entry(cur, user_id, amount, "STARTING_BALANCE", note="Welcome to Treasure Row")
        if own:
            conn.commit()
    except Exception:
        if own:
            conn.rollback()
        raise
    finally:
        if own:
            cur.close()
            conn.close()


def get_balance(user_id):
    ensure_wallet(user_id)
    conn = get_connection()
    cur = conn.cursor()
    try:
        return wm.get_wallet_balance(cur, user_id)
    finally:
        cur.close()
        conn.close()


# ---------------------------------------------------------------- checkout hold

def seller_portions(priced_cart):
    """{seller_id: amount} for a cart already priced from the database."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        sellers = wm.get_listing_sellers(cur, {int(i["id"]) for i in priced_cart})
    finally:
        cur.close()
        conn.close()
    portions = {}
    for item in priced_cart:
        seller_id = sellers.get(int(item["id"]))
        if seller_id is None:
            raise TokenError(f"Item (ID {item['id']}) has no storefront and can't be paid for.")
        portions[seller_id] = portions.get(seller_id, Decimal("0")) + _money(item["price"]) * int(item["quantity"])
    return portions


def assert_can_afford(user_id, amount):
    balance = get_balance(user_id)
    if balance < _money(amount):
        raise TokenError(
            f"Not enough Treasure Tokens: this order costs {_money(amount)} {TOKEN_UNIT} "
            f"and your balance is {balance} {TOKEN_UNIT}.", status=402)


def hold_escrow(order_id, buyer_id, portions):
    """Debit the buyer and create one escrow per seller, all in one transaction.
    Returns [{escrow_id, seller_id, amount, pickup_code}]."""
    ensure_wallet(buyer_id)
    total = sum(portions.values(), Decimal("0"))
    conn = get_connection()
    cur = conn.cursor()
    try:
        balance = wm.get_wallet_balance(cur, buyer_id, for_update=True)  # locks the wallet row
        if balance is None or balance < total:
            raise TokenError(
                f"Not enough Treasure Tokens: this order costs {total} {TOKEN_UNIT} "
                f"and your balance is {balance or 0} {TOKEN_UNIT}.", status=402)
        wm.change_balance(cur, buyer_id, -total)
        held = []
        for seller_id, amount in portions.items():
            nonce = secrets.token_hex(16)
            escrow_id = wm.insert_escrow(cur, order_id, buyer_id, seller_id, amount, nonce)
            wm.add_ledger_entry(cur, buyer_id, -amount, "ESCROW_HOLD", order_id=order_id,
                                escrow_id=escrow_id, note="Held in escrow until pickup")
            held.append({"escrow_id": escrow_id, "seller_id": seller_id, "amount": float(amount),
                         "pickup_code": pickup_code(escrow_id, nonce)})
        conn.commit()
        return held
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


# ------------------------------------------------------------- release / refund

def release_escrow(current_user, escrow_id, entered_code):
    """Seller confirms pickup with the buyer's code; tokens move to the seller."""
    if not current_user or current_user.get("id") is None:
        raise TokenError("Please sign in.", 401)
    conn = get_connection()
    cur = conn.cursor()
    try:
        escrow = wm.get_escrow(cur, escrow_id, for_update=True)
        if escrow is None:
            raise TokenError("Pickup not found.", 404)
        if escrow["seller_id"] != current_user["id"]:
            raise TokenError("Only the seller can confirm this pickup.", 403)
        if escrow["status"] == "LOCKED":
            raise TokenError("Too many wrong codes — this pickup is locked. Ask an admin to review it.", 423)
        if escrow["status"] != "HELD":
            raise TokenError(f"This pickup is already {escrow['status'].lower()}.", 409)

        if not _code_matches(escrow, entered_code):
            used = wm.record_failed_attempt(cur, escrow_id, MAX_CODE_ATTEMPTS)
            conn.commit()
            left = MAX_CODE_ATTEMPTS - used
            if left <= 0:
                raise TokenError("Wrong code. This pickup is now locked — ask an admin to review it.", 423)
            raise TokenError(f"Wrong pickup code. {left} attempt{'s' if left != 1 else ''} left.", 400)

        ensure_wallet(escrow["seller_id"], cur)
        wm.set_escrow_status(cur, escrow_id, "RELEASED")
        wm.change_balance(cur, escrow["seller_id"], escrow["amount"])
        wm.add_ledger_entry(cur, escrow["seller_id"], escrow["amount"], "ESCROW_RELEASE",
                            order_id=escrow["order_id"], escrow_id=escrow_id, note="Pickup confirmed")
        wm.update_order_status_from_escrow(cur, escrow["order_id"])
        conn.commit()
        return {"escrow_id": escrow_id, "status": "RELEASED", "amount": float(escrow["amount"])}
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def cancel_escrow(current_user, escrow_id, reason=None):
    """Buyer, seller, or admin cancels before pickup; the buyer is refunded."""
    if not current_user:
        raise TokenError("Please sign in.", 401)
    conn = get_connection()
    cur = conn.cursor()
    try:
        escrow = wm.get_escrow(cur, escrow_id, for_update=True)
        if escrow is None:
            raise TokenError("Pickup not found.", 404)
        is_admin = current_user.get("role") == "admin"
        if not is_admin and current_user.get("id") not in (escrow["buyer_id"], escrow["seller_id"]):
            raise TokenError("You can't cancel this order.", 403)
        if escrow["status"] not in ("HELD", "LOCKED"):
            raise TokenError(f"This pickup is already {escrow['status'].lower()}.", 409)

        who = "admin" if is_admin else ("buyer" if current_user["id"] == escrow["buyer_id"] else "seller")
        wm.set_escrow_status(cur, escrow_id, "REFUNDED")
        wm.change_balance(cur, escrow["buyer_id"], escrow["amount"])
        wm.add_ledger_entry(cur, escrow["buyer_id"], escrow["amount"], "ESCROW_REFUND",
                            order_id=escrow["order_id"], escrow_id=escrow_id,
                            note=f"Cancelled by {who}" + (f": {reason}" if reason else ""),
                            created_by=current_user.get("username"))
        wm.update_order_status_from_escrow(cur, escrow["order_id"])
        conn.commit()
        return {"escrow_id": escrow_id, "status": "REFUNDED", "amount": float(escrow["amount"])}
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


# ----------------------------------------------------------------- admin grant

def admin_grant(admin_user, user_id, amount, note=None):
    if not admin_user or admin_user.get("role") != "admin":
        raise TokenError("Admins only.", 403)
    try:
        amount = _money(amount)
    except (InvalidOperation, TypeError, ValueError):
        raise TokenError("Amount must be a number.")
    if amount <= 0 or amount > MAX_ADMIN_GRANT:
        raise TokenError(f"Amount must be between 0.01 and {MAX_ADMIN_GRANT} {TOKEN_UNIT}.")

    conn = get_connection()
    cur = conn.cursor()
    try:
        if not wm.user_exists(cur, user_id):
            raise TokenError("User not found.", 404)
        ensure_wallet(user_id, cur)
        wm.get_wallet_balance(cur, user_id, for_update=True)
        balance = wm.change_balance(cur, user_id, amount)
        wm.add_ledger_entry(cur, user_id, amount, "ADMIN_GRANT", note=(note or "")[:200] or None,
                            created_by=admin_user.get("username") or "admin")
        conn.commit()
        return {"user_id": user_id, "granted": float(amount), "balance": float(balance)}
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


# ------------------------------------------------------------------ read views

def _public_escrow(e, show_code):
    out = {
        "escrow_id": e["id"], "order_id": e["order_id"], "amount": float(e["amount"]),
        "status": e["status"], "confirmation_number": e.get("confirmation_number"),
        "seller_brand": e.get("seller_brand"), "buyer_name": e.get("buyer_name"),
        "meeting_location": e.get("meeting_location"),
        "created_at": e["created_at"].isoformat() if e.get("created_at") else None,
        "attempts_left": max(0, MAX_CODE_ATTEMPTS - e["failed_attempts"]),
    }
    if show_code and e["status"] == "HELD":
        out["pickup_code"] = pickup_code(e["id"], e["code_nonce"])
    return out


def wallet_summary(user_id):
    balance = get_balance(user_id)
    return {
        "unit": TOKEN_UNIT,
        "balance": float(balance),
        "ledger": wm.get_ledger(user_id),
        "purchases": [_public_escrow(e, show_code=True) for e in wm.list_escrows(user_id, "buyer")],
        "sales": [_public_escrow(e, show_code=False) for e in wm.list_escrows(user_id, "seller")],
    }


def order_escrows_for_buyer(order_id, buyer_id):
    return [_public_escrow(e, show_code=True) for e in wm.list_order_escrows(order_id)
            if e["buyer_id"] == buyer_id]
