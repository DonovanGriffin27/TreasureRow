# The Vault Campus Marketplace
# CSC 405 Sp 26'
# Created for Wishlist feature by Elali McNair 3/3/26
# The frontend protion of this code is not finished or implemented yet. Therfore, this code is not oporational or properly implemented yet.

"""
models/wishlist_model.py

Purpose:
This file handles all direct database operations related to wishlists.

This file includes DB operations for:
- wishlist (user wishlists)

It will:
- Insert new wishlist items
- Retrieve wishlist data for a user
- Remove items from wishlist
- Check if item is in wishlist
- Return results as dictionaries
"""

from db import get_connection


def add_to_wishlist(user_id, listing_id):
    """
    Adds a listing to user's wishlist.
    Returns the created wishlist item as a dictionary.
    If already exists, returns the existing one.
    """
    conn = get_connection()
    cur = conn.cursor()

    query = """
        INSERT INTO wishlist (user_id, listing_id)
        VALUES (%s, %s)
        ON CONFLICT (user_id, listing_id) DO NOTHING
        RETURNING id, user_id, listing_id, added_date;
    """

    cur.execute(query, (user_id, listing_id))
    row = cur.fetchone()
    conn.commit()

    cur.close()
    conn.close()

    if row:
        return {
            "id": row[0],
            "user_id": row[1],
            "listing_id": row[2],
            "added_date": row[3],
        }
    return None  # Already exists


def get_wishlist_by_user_id(user_id):
    """
    Retrieves all wishlist items for a specific user.
    Returns a list of wishlist item dictionaries with listing details.
    """
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT w.id, w.user_id, w.listing_id, w.added_date,
               l.title, l.description, l.price, l.fulfillment_type, l.status,
               s.brand_name, s.logo_url,
               (SELECT li.image_url FROM listing_images li
                WHERE li.listing_id = l.id AND li.is_primary = TRUE
                LIMIT 1) AS image_url
        FROM wishlist w
        JOIN listings l ON w.listing_id = l.id
        JOIN storefronts s ON l.storefront_id = s.id
        WHERE w.user_id = %s AND l.status != 'DELETED'
        ORDER BY w.added_date DESC;
    """

    cur.execute(query, (user_id,))
    rows = cur.fetchall()

    cur.close()
    conn.close()

    wishlist_items = []
    for row in rows:
        wishlist_items.append({
            "id": row[0],
            "user_id": row[1],
            "listing_id": row[2],
            "added_date": row[3],
            "listing": {
                "title": row[4],
                "description": row[5],
                "price": float(row[6]),
                "fulfillment_type": row[7],
                "status": row[8],
                "image_url": row[11],
            },
            "storefront": {
                "brand_name": row[9],
                "logo_url": row[10],
            }
        })

    return wishlist_items


def remove_from_wishlist(user_id, listing_id):
    """
    Removes a listing from user's wishlist.
    Returns True if removed, False if not found.
    """
    conn = get_connection()
    cur = conn.cursor()

    query = """
        DELETE FROM wishlist
        WHERE user_id = %s AND listing_id = %s;
    """

    cur.execute(query, (user_id, listing_id))
    deleted = cur.rowcount > 0
    conn.commit()

    cur.close()
    conn.close()

    return deleted


def is_in_wishlist(user_id, listing_id):
    """
    Checks if a listing is in user's wishlist.
    Returns True if in wishlist, False otherwise.
    """
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT 1 FROM wishlist
        WHERE user_id = %s AND listing_id = %s;
    """

    cur.execute(query, (user_id, listing_id))
    row = cur.fetchone()

    cur.close()
    conn.close()

    return row is not None


def get_wishlist_item_by_id(wishlist_id):
    """
    Retrieves a specific wishlist item by its ID.
    Returns None if not found.
    """
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT w.id, w.user_id, w.listing_id, w.added_date,
               l.title, l.description, l.price, l.fulfillment_type, l.status,
               s.brand_name, s.logo_url
        FROM wishlist w
        JOIN listings l ON w.listing_id = l.id
        JOIN storefronts s ON l.storefront_id = s.id
        WHERE w.id = %s;
    """

    cur.execute(query, (wishlist_id,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    if row:
        return {
            "id": row[0],
            "user_id": row[1],
            "listing_id": row[2],
            "added_date": row[3],
            "listing": {
                "title": row[4],
                "description": row[5],
                "price": float(row[6]),
                "fulfillment_type": row[7],
                "status": row[8],
            },
            "storefront": {
                "brand_name": row[9],
                "logo_url": row[10],
            }
        }
    return None