# The Vault Campus Marketplace
# CSC 405 Sp 26'
# Created for Purchase History feature by Elali McNair 3/3/26
# The frontend protion of this code is not finished or implemented yet. Therfore, this code is not oporational or properly implemented yet.

"""
models/purchase_model.py

Purpose:
This file handles all direct database operations related to purchases.

This file includes DB operations for:
- purchases (user purchase history)

It will:
- Insert new purchase records
- Retrieve purchase data for a user
- Return results as dictionaries
"""

from db import get_connection


def create_purchase(user_id, listing_id, quantity, purchase_price):
    """
    Inserts a new purchase record and returns the created purchase as a dictionary.
    """
    conn = get_connection()
    cur = conn.cursor()

    query = """
        INSERT INTO purchases (user_id, listing_id, quantity, purchase_price)
        VALUES (%s, %s, %s, %s)
        RETURNING id, user_id, listing_id, quantity, purchase_price, purchase_date;
    """

    cur.execute(query, (user_id, listing_id, quantity, purchase_price))
    row = cur.fetchone()
    conn.commit()

    cur.close()
    conn.close()

    return {
        "id": row[0],
        "user_id": row[1],
        "listing_id": row[2],
        "quantity": row[3],
        "purchase_price": float(row[4]),
        "purchase_date": row[5],
    }


def get_purchases_by_user_id(user_id):
    """
    Retrieves all purchases for a specific user.
    Returns a list of purchase dictionaries.
    """
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT p.id, p.user_id, p.listing_id, p.quantity, p.purchase_price, p.purchase_date,
               l.title, l.description, l.price as current_price, l.fulfillment_type,
               s.brand_name, s.logo_url
        FROM purchases p
        JOIN listings l ON p.listing_id = l.id
        JOIN storefronts s ON l.storefront_id = s.id
        WHERE p.user_id = %s
        ORDER BY p.purchase_date DESC;
    """

    cur.execute(query, (user_id,))
    rows = cur.fetchall()

    cur.close()
    conn.close()

    purchases = []
    for row in rows:
        purchases.append({
            "id": row[0],
            "user_id": row[1],
            "listing_id": row[2],
            "quantity": row[3],
            "purchase_price": float(row[4]),
            "purchase_date": row[5],
            "listing": {
                "title": row[6],
                "description": row[7],
                "current_price": float(row[8]),
                "fulfillment_type": row[9],
            },
            "storefront": {
                "brand_name": row[10],
                "logo_url": row[11],
            }
        })

    return purchases


def get_purchase_by_id(purchase_id):
    """
    Retrieves a specific purchase by its ID.
    Returns None if not found.
    """
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT p.id, p.user_id, p.listing_id, p.quantity, p.purchase_price, p.purchase_date,
               l.title, l.description, l.price as current_price, l.fulfillment_type,
               s.brand_name, s.logo_url
        FROM purchases p
        JOIN listings l ON p.listing_id = l.id
        JOIN storefronts s ON l.storefront_id = s.id
        WHERE p.id = %s;
    """

    cur.execute(query, (purchase_id,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    if row:
        return {
            "id": row[0],
            "user_id": row[1],
            "listing_id": row[2],
            "quantity": row[3],
            "purchase_price": float(row[4]),
            "purchase_date": row[5],
            "listing": {
                "title": row[6],
                "description": row[7],
                "current_price": float(row[8]),
                "fulfillment_type": row[9],
            },
            "storefront": {
                "brand_name": row[10],
                "logo_url": row[11],
            }
        }
    return None