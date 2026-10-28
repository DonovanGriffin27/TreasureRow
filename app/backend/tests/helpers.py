# backend/tests/helpers.py
# Created by Donovan Griffin - Iteration 3
#
# Shared test-data helpers so each test creates the users / storefronts /
# listings it needs in the TEST database (instead of borrowing whatever rows
# happen to exist) and removes them afterwards.

import struct
import uuid
import zlib

from db import get_connection
from utils.auth_utils import hash_password

PASSWORD = "Test-pass-123"


def create_user(cur, label="user"):
    username = f"t_{label}_{uuid.uuid4().hex[:8]}"
    cur.execute(
        "INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, 'user') RETURNING id;",
        (username, hash_password(PASSWORD), f"{username}@my.hamptonu.edu"),
    )
    return {"username": username, "user_id": cur.fetchone()[0]}


def create_seller(cur, label="seller", quantity=5, price="10.00"):
    """A user with one storefront and one active, in-stock listing."""
    seller = create_user(cur, label)
    cur.execute(
        "INSERT INTO storefronts (owner_id, brand_name, bio) VALUES (%s, %s, %s) RETURNING id;",
        (seller["user_id"], f"Brand {seller['username']}", f"bio {label}"),
    )
    seller["storefront_id"] = cur.fetchone()[0]
    seller["title"] = f"Listing {seller['username']}"
    seller["bio"] = f"bio {label}"
    cur.execute(
        """INSERT INTO listings (storefront_id, title, price, fulfillment_type, quantity_on_hand)
           VALUES (%s, %s, %s, 'IN_STOCK', %s) RETURNING id;""",
        (seller["storefront_id"], seller["title"], price, quantity),
    )
    seller["listing_id"] = cur.fetchone()[0]
    return seller


def delete_users(user_ids):
    """Remove test users and everything that hangs off them."""
    user_ids = [u for u in user_ids if u is not None]
    if not user_ids:
        return
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM storefronts WHERE owner_id = ANY(%s);", (user_ids,))
    storefront_ids = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT id FROM listings WHERE storefront_id = ANY(%s);", (storefront_ids,))
    listing_ids = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT id FROM orders WHERE user_id = ANY(%s);", (user_ids,))
    order_ids = [r[0] for r in cur.fetchall()]

    statements = [
        ("DELETE FROM order_items WHERE order_id = ANY(%s);", order_ids),
        ("DELETE FROM orders WHERE id = ANY(%s);", order_ids),
        ("DELETE FROM wishlist WHERE user_id = ANY(%s) OR listing_id = ANY(%s);", (user_ids, listing_ids)),
        ("DELETE FROM cart_items WHERE user_id = ANY(%s);", user_ids),
        ("DELETE FROM returns WHERE user_id = ANY(%s);", user_ids),
        ("DELETE FROM listings WHERE id = ANY(%s);", listing_ids),
        ("DELETE FROM storefronts WHERE id = ANY(%s);", storefront_ids),
        ("DELETE FROM users WHERE id = ANY(%s);", user_ids),
    ]
    for sql, params in statements:
        cur.execute(sql, params if isinstance(params, tuple) else (params,))
    conn.commit()
    cur.close()
    conn.close()


def sign_in(client, user, role="user"):
    """Put a user into the client's server-side session (what /auth/login does)."""
    with client.session_transaction() as sess:
        sess.clear()
        sess["user"] = user["username"]
        sess["user_id"] = user["user_id"]
        sess["role"] = role


def png_bytes():
    """A real 1x1 PNG (uploads are checked for genuine image contents)."""
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00")) + chunk(b"IEND", b""))
