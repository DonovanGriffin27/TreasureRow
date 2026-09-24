# The Vault Campus Marketplace
# CSC 405 Sp 26'
# Updated by Day Ekoi - 4/22/26 - rewrote to match orders/order_items schema

from db import get_connection


def create_order(user_id, confirmation_number, buyer_first_name, buyer_last_name,
                 buyer_email, buyer_contact, buyer_meeting_location, total_amount):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO orders (user_id, confirmation_number, buyer_first_name, buyer_last_name,
                            buyer_email, buyer_contact, buyer_meeting_location, total_amount, order_status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'SUBMITTED')
        RETURNING id, user_id, confirmation_number, buyer_first_name, buyer_last_name,
                  buyer_email, buyer_contact, buyer_meeting_location, total_amount, order_status, created_at;
    """, (user_id, confirmation_number, buyer_first_name, buyer_last_name,
          buyer_email, buyer_contact, buyer_meeting_location, total_amount))
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return {
        "id": row[0],
        "user_id": row[1],
        "confirmation_number": row[2],
        "buyer_first_name": row[3],
        "buyer_last_name": row[4],
        "buyer_email": row[5],
        "buyer_contact": row[6],
        "buyer_meeting_location": row[7],
        "total_amount": float(row[8]),
        "order_status": row[9],
        "created_at": str(row[10]),
    }


def create_order_item(order_id, listing_id, item_name, quantity, price_at_purchase, selected_size=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO order_items (order_id, listing_id, item_name, quantity, price_at_purchase, selected_size)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, order_id, listing_id, item_name, quantity, price_at_purchase, selected_size;
    """, (order_id, listing_id, item_name, quantity, price_at_purchase, selected_size))
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return {
        "id": row[0],
        "order_id": row[1],
        "listing_id": row[2],
        "item_name": row[3],
        "quantity": row[4],
        "price_at_purchase": float(row[5]),
        "selected_size": row[6],
    }


def get_order_by_confirmation(confirmation_number):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, user_id, confirmation_number, buyer_first_name, buyer_last_name,
               buyer_email, buyer_contact, buyer_meeting_location, total_amount, order_status, created_at
        FROM orders
        WHERE confirmation_number = %s;
    """, (confirmation_number,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0],
        "user_id": row[1],
        "confirmation_number": row[2],
        "buyer_first_name": row[3],
        "buyer_last_name": row[4],
        "buyer_email": row[5],
        "buyer_contact": row[6],
        "buyer_meeting_location": row[7],
        "total_amount": float(row[8]),
        "order_status": row[9],
        "created_at": str(row[10]),
    }


def get_order_items_by_order_id(order_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, order_id, listing_id, item_name, quantity, price_at_purchase, selected_size
        FROM order_items
        WHERE order_id = %s
        ORDER BY id ASC;
    """, (order_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {
            "id": r[0],
            "order_id": r[1],
            "listing_id": r[2],
            "item_name": r[3],
            "quantity": r[4],
            "price_at_purchase": float(r[5]),
            "selected_size": r[6],
        }
        for r in rows
    ]


def get_orders_by_user_id(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, user_id, confirmation_number, buyer_first_name, buyer_last_name,
               buyer_email, total_amount, order_status, created_at
        FROM orders
        WHERE user_id = %s
        ORDER BY created_at DESC;
    """, (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {
            "id": r[0],
            "user_id": r[1],
            "confirmation_number": r[2],
            "buyer_first_name": r[3],
            "buyer_last_name": r[4],
            "buyer_email": r[5],
            "total_amount": float(r[6]),
            "order_status": r[7],
            "created_at": str(r[8]),
        }
        for r in rows
    ]


def remove_purchased_from_wishlist(user_id, listing_ids):
    """
    Removes wishlist entries for listings the user just purchased.
    Uses listing_id matching only — the wishlist has a UNIQUE(user_id, listing_id)
    constraint so there is at most one entry per listing per user.
    """
    if not listing_ids:
        return {"deleted_count": 0}
    # Filter out None values
    valid_ids = [int(lid) for lid in listing_ids if lid is not None]
    if not valid_ids:
        return {"deleted_count": 0}
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM wishlist WHERE user_id = %s AND listing_id = ANY(%s);",
        (user_id, valid_ids)
    )
    deleted_count = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return {"deleted_count": deleted_count}


def clear_cart_for_user(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM cart_items WHERE user_id = %s;", (user_id,))
    deleted_count = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return {"deleted_count": deleted_count}


def check_listing_availability(listing_id, quantity_requested):
    """Raises if the listing is sold out or has insufficient stock. Skips made-to-order items."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT title, status, quantity_on_hand, is_made_to_order FROM listings WHERE id = %s",
        (listing_id,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        raise Exception(f"Item (ID {listing_id}) is no longer available.")
    title, status, qty_on_hand, is_made_to_order = row
    if is_made_to_order:
        return
    if status == "SOLD_OUT":
        raise Exception(f'"{title}" is sold out.')
    if qty_on_hand is not None and int(qty_on_hand) < quantity_requested:
        raise Exception(
            f'"{title}" only has {qty_on_hand} in stock (you requested {quantity_requested}).'
        )


def update_listing_size_inventory(listing_id, size, purchased_qty):
    """Decrements per-size inventory and syncs listing quantity_on_hand after purchase."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT quantity FROM listing_sizes WHERE listing_id = %s AND size = %s",
        (listing_id, size)
    )
    size_row = cur.fetchone()
    if size_row is None or int(size_row[0]) < purchased_qty:
        cur.close()
        conn.close()
        available = int(size_row[0]) if size_row else 0
        raise Exception(
            f"Insufficient stock for listing {listing_id} size '{size}': "
            f"requested {purchased_qty}, available {available}."
        )
    cur.execute("""
        UPDATE listing_sizes
        SET quantity = GREATEST(0, quantity - %s)
        WHERE listing_id = %s AND size = %s;
    """, (purchased_qty, listing_id, size))
    cur.execute("""
        SELECT COALESCE(SUM(quantity), 0) FROM listing_sizes WHERE listing_id = %s;
    """, (listing_id,))
    total_qty = int(cur.fetchone()[0])
    new_status = "SOLD_OUT" if total_qty == 0 else None
    cur.execute("""
        UPDATE listings
        SET quantity_on_hand = %s,
            status = COALESCE(%s, CASE WHEN status = 'SOLD_OUT' AND %s > 0 THEN 'ACTIVE' ELSE status END),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s AND (is_made_to_order = FALSE OR is_made_to_order IS NULL);
    """, (total_qty, new_status, total_qty, listing_id))
    conn.commit()
    cur.close()
    conn.close()
