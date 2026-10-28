# Treasure Row Campus Marketplace
# Added by Cameron Ridgley - 10/27/26

"""
models/browse_model.py

Purpose:
Read-only queries for the Discover pages (New Drops and Hot!), which show
listings from every storefront at once instead of one storefront at a time.

It will:
- Return public listings (ACTIVE or SOLD_OUT) from active storefronts only
- Include each listing's brand name and logo, and its cover image
  (primary image first, otherwise the oldest image)
- Include popularity counts: units sold (from order_items) and how many
  users have it wishlisted
"""

from db import get_connection


# Sort orders the service layer is allowed to ask for. Values are fixed SQL,
# never user input.
ORDER_BY = {
    "new": "l.created_at DESC, l.id DESC",
    "hot": "popularity DESC, l.created_at DESC, l.id DESC",
}


def get_public_listings(sort="new", limit=60):
    """
    Returns public listings from every active storefront as a list of dicts.

    sort:  "new" (newest first) or "hot" (most popular first)
    limit: maximum number of listings to return
    """
    order_by = ORDER_BY[sort]

    conn = get_connection()
    cur = conn.cursor()

    # popularity: each unit sold counts 3, each wishlist save counts 1
    query = f"""
        SELECT l.id, l.storefront_id, s.brand_name, s.logo_url,
               l.title, l.price, l.fulfillment_type, l.quantity_on_hand,
               l.status, l.is_made_to_order, l.created_at,
               (SELECT li.image_url
                  FROM listing_images li
                 WHERE li.listing_id = l.id
                 ORDER BY li.is_primary DESC, li.created_at ASC, li.id ASC
                 LIMIT 1) AS image_url,
               COALESCE(sold.units, 0) AS units_sold,
               COALESCE(saved.saves, 0) AS wishlist_count,
               COALESCE(sold.units, 0) * 3 + COALESCE(saved.saves, 0) AS popularity
          FROM listings l
          JOIN storefronts s ON s.id = l.storefront_id
          LEFT JOIN (SELECT listing_id, SUM(quantity) AS units
                       FROM order_items
                      GROUP BY listing_id) sold ON sold.listing_id = l.id
          LEFT JOIN (SELECT listing_id, COUNT(*) AS saves
                       FROM wishlist
                      GROUP BY listing_id) saved ON saved.listing_id = l.id
         WHERE s.is_active = TRUE
           AND l.status IN ('ACTIVE', 'SOLD_OUT')
         ORDER BY {order_by}
         LIMIT %s;
    """

    try:
        cur.execute(query, (limit,))
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    listings = []
    for row in rows:
        listings.append({
            "id": row[0],
            "storefront_id": row[1],
            "brand_name": row[2],
            "brand_logo_url": row[3],
            "title": row[4],
            "price": float(row[5]),
            "fulfillment_type": row[6],
            "quantity_on_hand": row[7],
            "status": row[8],
            "is_made_to_order": bool(row[9]) if row[9] is not None else False,
            "created_at": row[10],
            "image_url": row[11],
            "units_sold": int(row[12]),
            "wishlist_count": int(row[13]),
            "popularity": int(row[14]),
        })

    return listings
