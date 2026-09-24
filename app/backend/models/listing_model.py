# The Vault Campus Marketplace
# CSC 405 Sp 26'
# Created by Day Ekoi - Iteration 3
# Updated by Day Ekoi - Iteration 5 - 4/20/26 - added primary image JOIN to get_listings_by_storefront_id

"""
models/listing_model.py

Purpose:
This file handles all direct database operations related to listings.

This file includes DB operations for:
- listings (core listing data)
- listing_images (image URLs + primary image)
- listing_sizes (size-based inventory)

It will:
- Insert new listing records
- Retrieve listing data
- Update listing data
- Soft delete listings (status = 'DELETED')
- Insert/retrieve/update/delete listing image records
- Insert/retrieve/update/delete listing size inventory records
- Return results as dictionaries
"""

from db import get_connection


# ________________________________________________________
# LISTINGS TABLE OPERATIONS
# ________________________________________________________

def create_listing(
    storefront_id,
    title,
    description,
    price,
    fulfillment_type,
    quantity_on_hand=None,
    sizes_available=None,
    status="ACTIVE",
    is_made_to_order=False
):
    """
    Inserts a new listing and returns the created listing as a dictionary.
    """
    conn = get_connection()
    cur = conn.cursor()

    query = """
        INSERT INTO listings
        (storefront_id, title, description, price, fulfillment_type, quantity_on_hand, sizes_available, status, is_made_to_order)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, storefront_id, title, description, price,
                  fulfillment_type, quantity_on_hand, sizes_available,
                  status, created_at, updated_at, is_made_to_order;
    """

    cur.execute(query, (
        storefront_id,
        title,
        description,
        price,
        fulfillment_type,
        quantity_on_hand,
        sizes_available,
        status,
        bool(is_made_to_order)
    ))

    row = cur.fetchone()
    conn.commit()

    cur.close()
    conn.close()

    return {
        "id": row[0],
        "storefront_id": row[1],
        "title": row[2],
        "description": row[3],
        "price": float(row[4]),
        "fulfillment_type": row[5],
        "quantity_on_hand": row[6],
        "sizes_available": row[7],
        "status": row[8],
        "created_at": row[9],
        "updated_at": row[10],
        "is_made_to_order": row[11],
    }


def get_listing_by_id(listing_id):
    """
    Retrieves a listing by its PK (id).
    Returns None if not found.
    """
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT l.id, l.storefront_id, l.title, l.description, l.price,
               l.fulfillment_type, l.quantity_on_hand, l.sizes_available,
               l.status, l.storefront_restore_status, l.deleted_restore_status,
               l.created_at, l.updated_at,
               li.image_url, l.is_made_to_order
        FROM listings l
        LEFT JOIN listing_images li
            ON li.listing_id = l.id AND li.is_primary = TRUE
        WHERE l.id = %s;
    """

    cur.execute(query, (listing_id,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "storefront_id": row[1],
        "title": row[2],
        "description": row[3],
        "price": float(row[4]),
        "fulfillment_type": row[5],
        "quantity_on_hand": row[6],
        "sizes_available": row[7],
        "status": row[8],
        "storefront_restore_status": row[9],
        "deleted_restore_status": row[10],
        "created_at": row[11],
        "updated_at": row[12],
        "image_url": row[13],
        "is_made_to_order": bool(row[14]) if row[14] is not None else False,
    }


def get_listings_by_storefront_id(storefront_id, include_deleted=False):
    """
    Retrieves all non-deleted listings for a storefront.
    Returns a list of listing dictionaries.
    """
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT l.id, l.storefront_id, l.title, l.description, l.price,
               l.fulfillment_type, l.quantity_on_hand, l.sizes_available,
               l.status, l.storefront_restore_status, l.deleted_restore_status,
               l.created_at, l.updated_at,
               li.image_url, l.is_made_to_order
        FROM listings l
        LEFT JOIN listing_images li
            ON li.listing_id = l.id AND li.is_primary = TRUE
        WHERE l.storefront_id = %s
          AND (%s = TRUE OR l.status != 'DELETED')
        ORDER BY l.created_at DESC;
    """

    cur.execute(query, (storefront_id, include_deleted))
    rows = cur.fetchall()

    cur.close()
    conn.close()

    listings = []
    for row in rows:
        listings.append({
            "id": row[0],
            "storefront_id": row[1],
            "title": row[2],
            "description": row[3],
            "price": float(row[4]),
            "fulfillment_type": row[5],
            "quantity_on_hand": row[6],
            "sizes_available": row[7],
            "status": row[8],
            "storefront_restore_status": row[9],
            "deleted_restore_status": row[10],
            "created_at": row[11],
            "updated_at": row[12],
            "image_url": row[13],
            "is_made_to_order": bool(row[14]) if row[14] is not None else False,
        })

    return listings


def update_listing(
    listing_id,
    title=None,
    description=None,
    price=None,
    fulfillment_type=None,
    quantity_on_hand=None,
    sizes_available=None,
    status=None,
    is_made_to_order=None
):
    """
    Updates editable listing fields using COALESCE and returns updated listing.
    Returns None if listing does not exist.
    """
    conn = get_connection()
    cur = conn.cursor()

    query = """
        UPDATE listings
        SET title = COALESCE(%s, title),
            description = COALESCE(%s, description),
            price = COALESCE(%s, price),
            fulfillment_type = COALESCE(%s, fulfillment_type),
            quantity_on_hand = COALESCE(%s, quantity_on_hand),
            sizes_available = COALESCE(%s, sizes_available),
            status = COALESCE(%s, status),
            is_made_to_order = COALESCE(%s, is_made_to_order),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        RETURNING id, storefront_id, title, description, price,
                  fulfillment_type, quantity_on_hand, sizes_available,
                  status, created_at, updated_at, is_made_to_order;
    """

    cur.execute(query, (
        title,
        description,
        price,
        fulfillment_type,
        quantity_on_hand,
        sizes_available,
        status,
        is_made_to_order,
        listing_id
    ))

    row = cur.fetchone()
    conn.commit()

    cur.close()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "storefront_id": row[1],
        "title": row[2],
        "description": row[3],
        "price": float(row[4]),
        "fulfillment_type": row[5],
        "quantity_on_hand": row[6],
        "sizes_available": row[7],
        "status": row[8],
        "created_at": row[9],
        "updated_at": row[10],
        "is_made_to_order": bool(row[11]) if row[11] is not None else False,
    }


def soft_delete_listing(listing_id):
    """
    Soft deletes a listing by setting status = 'DELETED'.
    """
    conn = get_connection()
    cur = conn.cursor()

    query = """
        UPDATE listings
        SET deleted_restore_status = COALESCE(storefront_restore_status, status),
            storefront_restore_status = NULL,
            status = 'DELETED',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        RETURNING id, storefront_id, title, description, price,
                  fulfillment_type, quantity_on_hand, sizes_available,
                  status, created_at, updated_at, is_made_to_order;
    """

    cur.execute(query, (listing_id,))
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "storefront_id": row[1],
        "title": row[2],
        "description": row[3],
        "price": float(row[4]),
        "fulfillment_type": row[5],
        "quantity_on_hand": row[6],
        "sizes_available": row[7],
        "status": row[8],
        "created_at": row[9],
        "updated_at": row[10],
        "is_made_to_order": bool(row[11]) if row[11] is not None else False,
    }


def deactivate_listing(listing_id):
    return update_listing_status(listing_id, "INACTIVE", storefront_restore_status=None, deleted_restore_status=None)


def reactivate_listing(listing_id, restored_status):
    return update_listing_status(listing_id, restored_status, storefront_restore_status=None, deleted_restore_status=None)


def restore_deleted_listing(listing_id, restored_status, storefront_restore_status=None):
    return update_listing_status(
        listing_id,
        restored_status,
        storefront_restore_status=storefront_restore_status,
        deleted_restore_status=None
    )


def update_listing_status(listing_id, status, storefront_restore_status=None, deleted_restore_status=None):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        UPDATE listings
        SET status = %s,
            storefront_restore_status = %s,
            deleted_restore_status = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        RETURNING id, storefront_id, title, description, price,
                  fulfillment_type, quantity_on_hand, sizes_available,
                  status, storefront_restore_status, deleted_restore_status,
                  created_at, updated_at, is_made_to_order;
    """

    cur.execute(query, (status, storefront_restore_status, deleted_restore_status, listing_id))
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "storefront_id": row[1],
        "title": row[2],
        "description": row[3],
        "price": float(row[4]),
        "fulfillment_type": row[5],
        "quantity_on_hand": row[6],
        "sizes_available": row[7],
        "status": row[8],
        "storefront_restore_status": row[9],
        "deleted_restore_status": row[10],
        "created_at": row[11],
        "updated_at": row[12],
        "is_made_to_order": bool(row[13]) if row[13] is not None else False,
    }


def deactivate_active_listings_for_storefront(storefront_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE listings
        SET storefront_restore_status = status,
            status = 'INACTIVE',
            updated_at = CURRENT_TIMESTAMP
        WHERE storefront_id = %s
          AND status IN ('ACTIVE', 'SOLD_OUT');
    """, (storefront_id,))
    updated_count = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return updated_count


def restore_listings_after_storefront_reactivation(storefront_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE listings
        SET status = storefront_restore_status,
            storefront_restore_status = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE storefront_id = %s
          AND status = 'INACTIVE'
          AND storefront_restore_status IS NOT NULL;
    """, (storefront_id,))
    updated_count = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return updated_count


# ________________________________________________________
# LISTING IMAGES TABLE OPERATIONS
# ________________________________________________________

def add_listing_image(listing_id, image_url, is_primary=False):
    """
    Adds an image URL to a listing.
    Returns the created image record as a dictionary.
    """
    conn = get_connection()
    cur = conn.cursor()

    if is_primary:
        cur.execute(
            "UPDATE listing_images SET is_primary = FALSE WHERE listing_id = %s;",
            (listing_id,)
        )

    query = """
        INSERT INTO listing_images (listing_id, image_url, is_primary)
        VALUES (%s, %s, %s)
        RETURNING id, listing_id, image_url, is_primary, created_at;
    """
    cur.execute(query, (listing_id, image_url, is_primary))
    row = cur.fetchone()
    conn.commit()

    cur.close()
    conn.close()

    return {
        "id": row[0],
        "listing_id": row[1],
        "image_url": row[2],
        "is_primary": row[3],
        "created_at": row[4],
    }


def get_images_for_listing(listing_id):
    """
    Returns all images for a listing (primary first).
    """
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT id, listing_id, image_url, is_primary, created_at
        FROM listing_images
        WHERE listing_id = %s
        ORDER BY is_primary DESC, created_at ASC;
    """
    cur.execute(query, (listing_id,))
    rows = cur.fetchall()

    cur.close()
    conn.close()

    images = []
    for row in rows:
        images.append({
            "id": row[0],
            "listing_id": row[1],
            "image_url": row[2],
            "is_primary": row[3],
            "created_at": row[4],
        })

    return images


def set_primary_image(listing_id, image_id):
    """
    Marks a specific image as the primary image for that listing.
    Returns the updated image record, or None if not found.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "UPDATE listing_images SET is_primary = FALSE WHERE listing_id = %s;",
        (listing_id,)
    )

    query = """
        UPDATE listing_images
        SET is_primary = TRUE
        WHERE id = %s AND listing_id = %s
        RETURNING id, listing_id, image_url, is_primary, created_at;
    """
    cur.execute(query, (image_id, listing_id))
    row = cur.fetchone()
    conn.commit()

    cur.close()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "listing_id": row[1],
        "image_url": row[2],
        "is_primary": row[3],
        "created_at": row[4],
    }


def delete_listing_image(image_id):
    """
    Deletes an image record by image_id.
    Returns True if something was deleted, False otherwise.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM listing_images WHERE id = %s;", (image_id,))
    deleted = cur.rowcount > 0
    conn.commit()

    cur.close()
    conn.close()

    return deleted


# ________________________________________________________
# LISTING SIZES TABLE OPERATIONS
# ________________________________________________________

def upsert_listing_size(listing_id, size, quantity):
    """
    Creates or updates a size row for a listing.
    Updates quantity if (listing_id, size) already exists.
    Returns the upserted row as a dictionary.
    """
    conn = get_connection()
    cur = conn.cursor()

    query = """
        INSERT INTO listing_sizes (listing_id, size, quantity)
        VALUES (%s, %s, %s)
        ON CONFLICT (listing_id, size)
        DO UPDATE SET quantity = EXCLUDED.quantity
        RETURNING id, listing_id, size, quantity, created_at;
    """
    cur.execute(query, (listing_id, size, quantity))
    row = cur.fetchone()
    conn.commit()

    cur.close()
    conn.close()

    return {
        "id": row[0],
        "listing_id": row[1],
        "size": row[2],
        "quantity": row[3],
        "created_at": row[4],
    }


def get_sizes_for_listing(listing_id):
    """
    Returns all size inventory rows for a listing.
    """
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT id, listing_id, size, quantity, created_at
        FROM listing_sizes
        WHERE listing_id = %s
        ORDER BY size ASC;
    """
    cur.execute(query, (listing_id,))
    rows = cur.fetchall()

    cur.close()
    conn.close()

    sizes = []
    for row in rows:
        sizes.append({
            "id": row[0],
            "listing_id": row[1],
            "size": row[2],
            "quantity": row[3],
            "created_at": row[4],
        })

    return sizes


def delete_listing_size(listing_id, size):
    """
    Deletes a size row for a listing.
    Returns True if something was deleted, False otherwise.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM listing_sizes WHERE listing_id = %s AND size = %s;",
        (listing_id, size)
    )
    deleted = cur.rowcount > 0
    conn.commit()

    cur.close()
    conn.close()

    return deleted
