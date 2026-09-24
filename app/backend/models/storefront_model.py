# The Vault Campus Marketplace
# CSC 405 Sp 26'
# Created by Day Ekoi - Iteration 3
# Updated by Day Ekoi - Iteration 5 - 4/10/26 -4/20/26 - added preview_image_1-4 to all queries, added item_count via JOIN, fixed contact_info column

"""
models/storefront_model.py

Purpose:
This file is responsible for direct communication with the `storefronts` table
in the PostgreSQL database using psycopg2.

This file will:
- Execute SQL queries related to storefronts
- Insert new storefront records
- Retrieve storefront data
- Update storefront data
- Return database results in a structured (dictionary) format
"""

from db import get_connection


def create_storefront(owner_id, brand_name, bio=None, logo_url=None, banner_url=None, contact_info=None,
                      preview_image_1=None, preview_image_2=None, preview_image_3=None, preview_image_4=None,
                      categories=None):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        INSERT INTO storefronts (owner_id, brand_name, bio, logo_url, banner_url, contact_info,
                                 preview_image_1, preview_image_2, preview_image_3, preview_image_4,
                                 categories)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, owner_id, brand_name, bio, logo_url, banner_url, contact_info,
                  preview_image_1, preview_image_2, preview_image_3, preview_image_4,
                  categories, is_active, created_at, updated_at;
    """

    cur.execute(query, (owner_id, brand_name, bio, logo_url, banner_url, contact_info,
                        preview_image_1, preview_image_2, preview_image_3, preview_image_4,
                        categories))
    row = cur.fetchone()
    conn.commit()

    cur.close()
    conn.close()

    return {
        "id": row[0],
        "owner_id": row[1],
        "brand_name": row[2],
        "bio": row[3],
        "logo_url": row[4],
        "banner_url": row[5],
        "contact_info": row[6],
        "preview_image_1": row[7],
        "preview_image_2": row[8],
        "preview_image_3": row[9],
        "preview_image_4": row[10],
        "categories": row[11],
        "is_active": row[12],
        "created_at": row[13],
        "updated_at": row[14],
    }


def get_storefront_by_id(storefront_id):
    """
    Retrieves a storefront by its primary key (id).
    Returns None if not found.
    """
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT s.id, s.owner_id, s.brand_name, s.bio, s.logo_url,
               s.banner_url, s.contact_info,
               s.preview_image_1, s.preview_image_2, s.preview_image_3, s.preview_image_4,
               s.categories, s.is_active, s.created_at, s.updated_at,
               COUNT(l.id) AS item_count
        FROM storefronts s
        LEFT JOIN listings l ON l.storefront_id = s.id AND l.status NOT IN ('DELETED', 'INACTIVE')
        WHERE s.id = %s
        GROUP BY s.id;
    """

    cur.execute(query, (storefront_id,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "owner_id": row[1],
        "brand_name": row[2],
        "bio": row[3],
        "logo_url": row[4],
        "banner_url": row[5],
        "contact_info": row[6],
        "preview_image_1": row[7],
        "preview_image_2": row[8],
        "preview_image_3": row[9],
        "preview_image_4": row[10],
        "categories": row[11],
        "is_active": row[12],
        "created_at": row[13],
        "updated_at": row[14],
        "item_count": row[15],
    }


def get_storefront_by_owner_id(owner_id):
    """
    Retrieves the storefront owned by a specific user (owner_id).
    """
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT s.id, s.owner_id, s.brand_name, s.bio, s.logo_url,
               s.banner_url, s.contact_info,
               s.preview_image_1, s.preview_image_2, s.preview_image_3, s.preview_image_4,
               s.categories, s.is_active, s.created_at, s.updated_at,
               COUNT(l.id) AS item_count
        FROM storefronts s
        LEFT JOIN listings l ON l.storefront_id = s.id AND l.status NOT IN ('DELETED', 'INACTIVE')
        WHERE s.owner_id = %s
        GROUP BY s.id;
    """

    cur.execute(query, (owner_id,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "owner_id": row[1],
        "brand_name": row[2],
        "bio": row[3],
        "logo_url": row[4],
        "banner_url": row[5],
        "contact_info": row[6],
        "preview_image_1": row[7],
        "preview_image_2": row[8],
        "preview_image_3": row[9],
        "preview_image_4": row[10],
        "categories": row[11],
        "is_active": row[12],
        "created_at": row[13],
        "updated_at": row[14],
        "item_count": row[15],
    }


def update_storefront(storefront_id, brand_name=None, bio=None, logo_url=None, banner_url=None, contact_info=None,
                      preview_image_1=None, preview_image_2=None, preview_image_3=None, preview_image_4=None,
                      categories=None):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        UPDATE storefronts
        SET brand_name = COALESCE(%s, brand_name),
            bio = COALESCE(%s, bio),
            logo_url = COALESCE(%s, logo_url),
            banner_url = COALESCE(%s, banner_url),
            contact_info = COALESCE(%s, contact_info),
            preview_image_1 = COALESCE(%s, preview_image_1),
            preview_image_2 = COALESCE(%s, preview_image_2),
            preview_image_3 = COALESCE(%s, preview_image_3),
            preview_image_4 = COALESCE(%s, preview_image_4),
            categories = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        RETURNING id, owner_id, brand_name, bio, logo_url, banner_url, contact_info,
                  preview_image_1, preview_image_2, preview_image_3, preview_image_4,
                  categories, is_active, created_at, updated_at;
    """

    cur.execute(query, (brand_name, bio, logo_url, banner_url, contact_info,
                        preview_image_1, preview_image_2, preview_image_3, preview_image_4,
                        categories, storefront_id))
    row = cur.fetchone()
    conn.commit()

    cur.close()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "owner_id": row[1],
        "brand_name": row[2],
        "bio": row[3],
        "logo_url": row[4],
        "banner_url": row[5],
        "contact_info": row[6],
        "preview_image_1": row[7],
        "preview_image_2": row[8],
        "preview_image_3": row[9],
        "preview_image_4": row[10],
        "categories": row[11],
        "is_active": row[12],
        "created_at": row[13],
        "updated_at": row[14],
    }


def set_storefront_active(storefront_id, is_active):
    """
    Activates or deactivates a storefront.
    This is a soft action often used for admin moderation or temporarily disabling a storefront.
    """
    conn = get_connection()
    cur = conn.cursor()

    query = """
        UPDATE storefronts
        SET is_active = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        RETURNING id, owner_id, brand_name, bio, logo_url, banner_url, contact_info,
                  preview_image_1, preview_image_2, preview_image_3, preview_image_4,
                  categories, is_active, created_at, updated_at;
    """

    cur.execute(query, (is_active, storefront_id))
    row = cur.fetchone()
    conn.commit()

    cur.close()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "owner_id": row[1],
        "brand_name": row[2],
        "bio": row[3],
        "logo_url": row[4],
        "banner_url": row[5],
        "contact_info": row[6],
        "preview_image_1": row[7],
        "preview_image_2": row[8],
        "preview_image_3": row[9],
        "preview_image_4": row[10],
        "categories": row[11],
        "is_active": row[12],
        "created_at": row[13],
        "updated_at": row[14],
    }


# ___________________________________________________________
#  Admin Queries ( needed for future development)
# ___________________________________________________________

def get_all_storefronts():
    """
    Returns all storefronts (active + inactive).
    Useful for admin moderation dashboards.
    """
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT s.id, s.owner_id, s.brand_name, s.bio, s.logo_url,
               s.banner_url, s.contact_info,
               s.preview_image_1, s.preview_image_2, s.preview_image_3, s.preview_image_4,
               s.categories, s.is_active, s.created_at, s.updated_at,
               COUNT(l.id) AS item_count
        FROM storefronts s
        LEFT JOIN listings l ON l.storefront_id = s.id AND l.status NOT IN ('DELETED', 'INACTIVE')
        GROUP BY s.id
        ORDER BY s.created_at DESC;
    """

    cur.execute(query)
    rows = cur.fetchall()

    cur.close()
    conn.close()

    storefronts = []
    for row in rows:
        storefronts.append({
            "id": row[0],
            "owner_id": row[1],
            "brand_name": row[2],
            "bio": row[3],
            "logo_url": row[4],
            "banner_url": row[5],
            "contact_info": row[6],
            "preview_image_1": row[7],
            "preview_image_2": row[8],
            "preview_image_3": row[9],
            "preview_image_4": row[10],
            "categories": row[11],
            "is_active": row[12],
            "created_at": row[13],
            "updated_at": row[14],
            "item_count": row[15],
        })

    return storefronts


def get_active_storefronts():
    """
    Returns only active storefronts.
    Useful for public browsing pages (non-admin views).
    """
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT s.id, s.owner_id, s.brand_name, s.bio, s.logo_url,
               s.banner_url, s.contact_info,
               s.preview_image_1, s.preview_image_2, s.preview_image_3, s.preview_image_4,
               s.categories, s.is_active, s.created_at, s.updated_at,
               COUNT(l.id) AS item_count
        FROM storefronts s
        LEFT JOIN listings l ON l.storefront_id = s.id AND l.status NOT IN ('DELETED', 'INACTIVE')
        WHERE s.is_active = TRUE
        GROUP BY s.id
        ORDER BY s.created_at DESC;
    """

    cur.execute(query)
    rows = cur.fetchall()

    cur.close()
    conn.close()

    storefronts = []
    for row in rows:
        storefronts.append({
            "id": row[0],
            "owner_id": row[1],
            "brand_name": row[2],
            "bio": row[3],
            "logo_url": row[4],
            "banner_url": row[5],
            "contact_info": row[6],
            "preview_image_1": row[7],
            "preview_image_2": row[8],
            "preview_image_3": row[9],
            "preview_image_4": row[10],
            "categories": row[11],
            "is_active": row[12],
            "created_at": row[13],
            "updated_at": row[14],
            "item_count": row[15],
        })

    return storefronts
