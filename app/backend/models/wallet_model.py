"""
wallet_model.py

Treasure Row Campus Marketplace
Created by Donovan Griffin - Iteration 3

SQL for the Treasure Tokens payment system: wallets, the token ledger, and
order escrow. Functions take a cursor so the service layer can run several of
them inside one database transaction (money moves must be all-or-nothing).
"""

from db import get_connection


# ---------------------------------------------------------------- wallets

def get_wallet_balance(cur, user_id, for_update=False):
    """Current balance, or None if the user has no wallet yet.
    for_update=True locks the row until the transaction ends."""
    cur.execute(
        "SELECT balance FROM wallets WHERE user_id = %s" + (" FOR UPDATE" if for_update else "") + ";",
        (user_id,),
    )
    row = cur.fetchone()
    return row[0] if row else None


def insert_wallet_if_missing(cur, user_id, balance):
    """Create a wallet; returns True if this call created it (False if it already existed)."""
    cur.execute(
        "INSERT INTO wallets (user_id, balance) VALUES (%s, %s) ON CONFLICT (user_id) DO NOTHING RETURNING user_id;",
        (user_id, balance),
    )
    return cur.fetchone() is not None


def change_balance(cur, user_id, delta):
    """Add delta (negative to debit). The CHECK (balance >= 0) constraint makes
    an overdraft fail at the database level."""
    cur.execute(
        "UPDATE wallets SET balance = balance + %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s RETURNING balance;",
        (delta, user_id),
    )
    row = cur.fetchone()
    return row[0] if row else None


def add_ledger_entry(cur, user_id, amount, entry_type, order_id=None, escrow_id=None, note=None, created_by=None):
    cur.execute(
        """INSERT INTO token_ledger (user_id, amount, entry_type, order_id, escrow_id, note, created_by)
           VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;""",
        (user_id, amount, entry_type, order_id, escrow_id, note, created_by),
    )
    return cur.fetchone()[0]


def get_ledger(user_id, limit=50):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT l.id, l.amount, l.entry_type, l.note, l.created_at, o.confirmation_number
           FROM token_ledger l LEFT JOIN orders o ON o.id = l.order_id
           WHERE l.user_id = %s ORDER BY l.created_at DESC, l.id DESC LIMIT %s;""",
        (user_id, limit),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"id": r[0], "amount": float(r[1]), "type": r[2], "note": r[3],
             "created_at": r[4].isoformat() if r[4] else None, "confirmation_number": r[5]} for r in rows]


def get_all_wallets():
    """Every user with their balance (admin view). Users without a wallet show balance None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT u.id, u.username, u.email, u.role, w.balance
           FROM users u LEFT JOIN wallets w ON w.user_id = u.id ORDER BY u.id;"""
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"user_id": r[0], "username": r[1], "email": r[2], "role": r[3],
             "balance": float(r[4]) if r[4] is not None else None} for r in rows]


def user_exists(cur, user_id):
    cur.execute("SELECT 1 FROM users WHERE id = %s;", (user_id,))
    return cur.fetchone() is not None


# ----------------------------------------------------------------- escrow

def get_listing_sellers(cur, listing_ids):
    """{listing_id: seller (storefront owner) user id} for the given listings."""
    cur.execute(
        """SELECT l.id, s.owner_id FROM listings l JOIN storefronts s ON s.id = l.storefront_id
           WHERE l.id = ANY(%s);""",
        (list(listing_ids),),
    )
    return {r[0]: r[1] for r in cur.fetchall()}


def insert_escrow(cur, order_id, buyer_id, seller_id, amount, code_nonce):
    cur.execute(
        """INSERT INTO order_escrow (order_id, buyer_id, seller_id, amount, code_nonce)
           VALUES (%s, %s, %s, %s, %s) RETURNING id;""",
        (order_id, buyer_id, seller_id, amount, code_nonce),
    )
    return cur.fetchone()[0]


_ESCROW_COLUMNS = "id, order_id, buyer_id, seller_id, amount, status, code_nonce, failed_attempts, created_at, resolved_at"


def _escrow_row(r):
    return {"id": r[0], "order_id": r[1], "buyer_id": r[2], "seller_id": r[3], "amount": r[4],
            "status": r[5], "code_nonce": r[6], "failed_attempts": r[7],
            "created_at": r[8], "resolved_at": r[9]}


def get_escrow(cur, escrow_id, for_update=False):
    cur.execute(
        f"SELECT {_ESCROW_COLUMNS} FROM order_escrow WHERE id = %s" + (" FOR UPDATE" if for_update else "") + ";",
        (escrow_id,),
    )
    row = cur.fetchone()
    return _escrow_row(row) if row else None


def set_escrow_status(cur, escrow_id, status):
    cur.execute(
        "UPDATE order_escrow SET status = %s, resolved_at = CASE WHEN %s IN ('RELEASED','REFUNDED') "
        "THEN CURRENT_TIMESTAMP ELSE resolved_at END WHERE id = %s;",
        (status, status, escrow_id),
    )


def record_failed_attempt(cur, escrow_id, max_attempts):
    """Count a wrong pickup code; lock the escrow when the limit is reached. Returns attempts used."""
    cur.execute(
        """UPDATE order_escrow
           SET failed_attempts = failed_attempts + 1,
               status = CASE WHEN failed_attempts + 1 >= %s THEN 'LOCKED' ELSE status END
           WHERE id = %s RETURNING failed_attempts;""",
        (max_attempts, escrow_id),
    )
    return cur.fetchone()[0]


def update_order_status_from_escrow(cur, order_id):
    """COMPLETED once every seller's escrow is released, CANCELLED once all are refunded."""
    cur.execute("SELECT status FROM order_escrow WHERE order_id = %s;", (order_id,))
    statuses = {r[0] for r in cur.fetchall()}
    if statuses == {"RELEASED"}:
        new_status = "COMPLETED"
    elif statuses == {"REFUNDED"}:
        new_status = "CANCELLED"
    elif statuses <= {"RELEASED", "REFUNDED"}:
        new_status = "PARTIALLY_COMPLETED"
    else:
        return
    cur.execute("UPDATE orders SET order_status = %s WHERE id = %s;", (new_status, order_id))


def list_escrows(user_id, role):
    """Escrows where the user is the buyer (role='buyer') or the seller (role='seller'),
    newest first, with order and counterpart details."""
    column = "e.buyer_id" if role == "buyer" else "e.seller_id"
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"""SELECT {', '.join('e.' + c.strip() for c in _ESCROW_COLUMNS.split(','))},
                   o.confirmation_number, o.buyer_first_name, o.buyer_last_name, o.buyer_meeting_location,
                   s.brand_name
            FROM order_escrow e
            JOIN orders o ON o.id = e.order_id
            LEFT JOIN storefronts s ON s.owner_id = e.seller_id
            WHERE {column} = %s
            ORDER BY e.created_at DESC, e.id DESC;""",
        (user_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    out = []
    for r in rows:
        e = _escrow_row(r[:10])
        e.update({"confirmation_number": r[10], "buyer_name": f"{r[11]} {r[12]}".strip(),
                  "meeting_location": r[13], "seller_brand": r[14]})
        out.append(e)
    return out


def list_order_escrows(order_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"""SELECT {', '.join('e.' + c.strip() for c in _ESCROW_COLUMNS.split(','))}, s.brand_name
            FROM order_escrow e LEFT JOIN storefronts s ON s.owner_id = e.seller_id
            WHERE e.order_id = %s ORDER BY e.id;""",
        (order_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    out = []
    for r in rows:
        e = _escrow_row(r[:10])
        e["seller_brand"] = r[10]
        out.append(e)
    return out
