"""
Author: Jonah Goodwine
Created: 10/24/26
CSC404
message_model.py -- SQL for the messaging feature (uses the messages table in init_db.py)
"""

from db import get_connection


# returns the username for a user id, or nothing
def get_username(userId):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT username FROM users
            WHERE id = %s;
    """

    cur.execute(query, (userId,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    if row:
        return row[0]
    return None


# returns the title of a listing, or nothing
def get_listing_title(listingId):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT title FROM listings
            WHERE id = %s;
    """

    cur.execute(query, (listingId,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    if row:
        return row[0]
    return None


# saves one message and returns its new id
def send_message(senderId, receiverId, listingId, body):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        INSERT INTO messages (sender_id, receiver_id, listing_id, body)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
    """

    cur.execute(query, (senderId, receiverId, listingId, body))
    newId = cur.fetchone()[0]
    conn.commit()

    cur.close()
    conn.close()

    return newId


# every message the user sent or received, newest first
# returns (sender_id, receiver_id, listing_id, body, created_at, is_read,
#          sender_name, receiver_name, listing_title)
def get_all_for_user(userId):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT m.sender_id, m.receiver_id, m.listing_id, m.body, m.created_at, m.is_read,
               s.username, r.username, l.title
            FROM messages m
            JOIN users s ON s.id = m.sender_id
            JOIN users r ON r.id = m.receiver_id
            LEFT JOIN listings l ON l.id = m.listing_id
            WHERE m.sender_id = %s OR m.receiver_id = %s
            ORDER BY m.created_at DESC, m.id DESC;
    """

    cur.execute(query, (userId, userId))
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows


# one conversation between two users about one listing, oldest first
# listingId can be None for messages not tied to a listing
# returns (id, sender_id, sender_name, body, created_at)
def get_thread(userId, otherId, listingId):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT m.id, m.sender_id, s.username, m.body, m.created_at
            FROM messages m
            JOIN users s ON s.id = m.sender_id
            WHERE ((m.sender_id = %s AND m.receiver_id = %s)
                OR (m.sender_id = %s AND m.receiver_id = %s))
              AND m.listing_id IS NOT DISTINCT FROM %s
            ORDER BY m.created_at, m.id;
    """

    cur.execute(query, (userId, otherId, otherId, userId, listingId))
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows


# marks messages the other user sent me in this conversation as read
def mark_read(userId, otherId, listingId):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        UPDATE messages SET is_read = TRUE
            WHERE receiver_id = %s AND sender_id = %s
              AND listing_id IS NOT DISTINCT FROM %s
              AND is_read = FALSE;
    """

    cur.execute(query, (userId, otherId, listingId))
    conn.commit()

    cur.close()
    conn.close()