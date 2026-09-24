# By Elali McNair - Iteration 4
"""
create_listings.py

Purpose:
Create 1 listing for each existing active storefront in the database.

Run this script manually when:
- You want to populate listings for all storefronts without altering mock_data.py
- Testing storefront views with real data
"""

from db import get_connection


def create_listings_for_storefronts():
    conn = get_connection()
    cur = conn.cursor()

    try:
        # Query all active storefronts
        cur.execute("SELECT id FROM storefronts WHERE is_active = TRUE;")
        storefront_ids = [row[0] for row in cur.fetchall()]

        if not storefront_ids:
            print("No active storefronts found. Run mock_data.py first to create storefronts.")
            return

        # For each storefront, create 1 listing
        for i, storefront_id in enumerate(storefront_ids):
            title = f"Listing for Storefront {storefront_id}"
            cur.execute(
                """
                INSERT INTO listings
                    (storefront_id, title, description, price, fulfillment_type, quantity_on_hand, sizes_available, status)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    storefront_id,
                    title,
                    f"Sample listing description for storefront {storefront_id}.",
                    25.00 + i * 5,  # Vary prices slightly
                    "IN_STOCK",
                    10,
                    '["S","M","L","XL"]',
                    "ACTIVE",
                ),
            )

            row = cur.fetchone()
            if row:
                listing_id = row[0]

                # Add a primary image
                cur.execute(
                    """
                    INSERT INTO listing_images (listing_id, image_url, is_primary)
                    VALUES (%s, %s, %s);
                    """,
                    (listing_id, f"https://example.com/listing-{listing_id}.png", True),
                )

                # Add sizes
                sizes = [("S", 2), ("M", 3), ("L", 3), ("XL", 2)]
                for size, qty in sizes:
                    cur.execute(
                        """
                        INSERT INTO listing_sizes (listing_id, size, quantity)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (listing_id, size)
                        DO UPDATE SET quantity = EXCLUDED.quantity;
                        """,
                        (listing_id, size, qty),
                    )

        conn.commit()
        print(f"Created 1 listing for each of {len(storefront_ids)} storefronts.")

    except Exception as e:
        conn.rollback()
        print("Error creating listings:", e)

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    create_listings_for_storefronts()