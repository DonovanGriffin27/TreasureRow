"""
Author: Jonah Goodwine
Created: 9/30/26
CSC404
auth_model.py -- moves queries out of auth_controller.py
"""

from db import get_connection

# returns (id, username, role) or nothing
def get_user_by_username(username):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT id, username, role FROM users
            WHERE username = %s;
    """

    cur.execute(query, (username,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    return row

# returns -> (status, quantity_on_hand, is_made_to_order) or nothing
def get_listing_availability(itemId):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT status, quantity_on_hand, is_made_to_order FROM listings
            WHERE id = %s
    """

    cur.execute(query, (itemId,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    return row

# saves one item to the user's cart
def add_cart_item(userId, itemId, itemName, price, quantity, size):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        INSERT INTO cart_items(user_id, item_id, item_name, price, quantity, size)
            VALUES(%s, %s, %s, %s, %s, %s)    
    """

    cur.execute(query, (userId, itemId, itemName, price, quantity, size))
    conn.commit()

    cur.close()
    conn.close()

# removes one item from the user's cart
def remove_cart_item(userId, itemName, size):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        DELETE FROM cart_items
            WHERE id = (
                SELECT id FROM cart_items
                    WHERE user_id = %s AND item_name = %s AND size = %s
                    LIMIT 1
            );
    """

    cur.execute(query, (userId, itemName, size))
    conn.commit()

    cur.close()
    conn.close()