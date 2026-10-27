"""
init_db.py

Purpose:
This file initializes the PostgreSQL database schema for The Vault.
It creates all required database tables if they do not already exist.

Run this file manually when:
- Setting up the project for the first time
- Deploying to a new environment
- Ensuring the database schema is properly initialized
"""

# The Vault Campus Marketplace
# CSC 405 Sp 26'
# Updated - Iteration 5 - 4/20/26 - added contact_info, preview_image_1-4, categories columns to storefronts; added ALTER TABLE migrations

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

from db import get_connection


def create_vault_tables():
    try:
        # shared connection settings (SSL + timeout) - Donovan Griffin, Iteration 3
        conn = get_connection()

        cur = conn.cursor()

        # ________________________________________________________
        # USERS TABLE
        # ________________________________________________________
        create_users_table = """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                role VARCHAR(10) DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        cur.execute(create_users_table)

        # ________________________________________________________
        # STOREFRONTS TABLE (One storefront per user)
        # Updated 4/20/26 - added contact_info, preview_image_1-4 columns
        # ________________________________________________________
        create_storefronts_table = """
            CREATE TABLE IF NOT EXISTS storefronts (
                id SERIAL PRIMARY KEY,
                owner_id INTEGER NOT NULL UNIQUE,
                brand_name VARCHAR(80) NOT NULL,
                bio TEXT,
                logo_url TEXT,
                banner_url TEXT,
                contact_info TEXT,
                preview_image_1 TEXT,
                preview_image_2 TEXT,
                preview_image_3 TEXT,
                preview_image_4 TEXT,
                categories TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT fk_storefront_owner
                    FOREIGN KEY(owner_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            );
        """
        cur.execute(create_storefronts_table)

        # Migrations for existing databases - Added 4/20/26
        cur.execute("ALTER TABLE storefronts ADD COLUMN IF NOT EXISTS contact_info TEXT;")
        cur.execute("ALTER TABLE storefronts ADD COLUMN IF NOT EXISTS preview_image_1 TEXT;")
        cur.execute("ALTER TABLE storefronts ADD COLUMN IF NOT EXISTS preview_image_2 TEXT;")
        cur.execute("ALTER TABLE storefronts ADD COLUMN IF NOT EXISTS preview_image_3 TEXT;")
        cur.execute("ALTER TABLE storefronts ADD COLUMN IF NOT EXISTS preview_image_4 TEXT;")
        cur.execute("ALTER TABLE storefronts ADD COLUMN IF NOT EXISTS categories TEXT;")
        # Backfill is_active so existing rows are never NULL (NULL was treated as deactivated)
        cur.execute("ALTER TABLE storefronts ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;")
        cur.execute("UPDATE storefronts SET is_active = TRUE WHERE is_active IS NULL;")

        # ________________________________________________________
        # LISTINGS TABLE (Each listing belongs to a storefront)
        # ________________________________________________________
        create_listings_table = """
            CREATE TABLE IF NOT EXISTS listings (
                id SERIAL PRIMARY KEY,
                storefront_id INTEGER NOT NULL,

                title VARCHAR(120) NOT NULL,
                description TEXT,
                price NUMERIC(10,2) NOT NULL CHECK (price >= 0),

                fulfillment_type VARCHAR(20) NOT NULL
                    CHECK (fulfillment_type IN ('IN_STOCK', 'PREORDER')),

                quantity_on_hand INTEGER CHECK (quantity_on_hand >= 0),

                sizes_available TEXT,

                status VARCHAR(20) DEFAULT 'ACTIVE'
                    CHECK (status IN ('ACTIVE', 'INACTIVE', 'SOLD_OUT', 'DELETED')),

                storefront_restore_status VARCHAR(20),
                deleted_restore_status VARCHAR(20),

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT fk_listing_storefront
                    FOREIGN KEY(storefront_id)
                    REFERENCES storefronts(id)
                    ON DELETE CASCADE
            );
        """
        cur.execute(create_listings_table)
        cur.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS storefront_restore_status VARCHAR(20);")
        cur.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS deleted_restore_status VARCHAR(20);")
        cur.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS is_made_to_order BOOLEAN DEFAULT FALSE;")
        cur.execute("UPDATE listings SET is_made_to_order = FALSE WHERE is_made_to_order IS NULL;")

        # ________________________________________________________
        # LISTING IMAGES TABLE (Multiple images per listing)
        # ________________________________________________________
        create_listing_images_table = """
            CREATE TABLE IF NOT EXISTS listing_images (
                id SERIAL PRIMARY KEY,
                listing_id INTEGER NOT NULL,
                image_url TEXT NOT NULL,
                is_primary BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT fk_image_listing
                    FOREIGN KEY(listing_id)
                    REFERENCES listings(id)
                    ON DELETE CASCADE
            );
        """
        cur.execute(create_listing_images_table)

        # ________________________________________________________
        # LISTING SIZES TABLE (Inventory per size)
        # ________________________________________________________
        create_listing_sizes_table = """
            CREATE TABLE IF NOT EXISTS listing_sizes (
                id SERIAL PRIMARY KEY,
                listing_id INTEGER NOT NULL,
                size VARCHAR(20) NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity >= 0),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT fk_size_listing
                    FOREIGN KEY(listing_id)
                    REFERENCES listings(id)
                    ON DELETE CASCADE,

                CONSTRAINT unique_listing_size
                    UNIQUE (listing_id, size)
            );
        """
        cur.execute(create_listing_sizes_table)

        # ________________________________________________________
        # PURCHASES TABLE (Purchase history for users)
        # The frontend protion of this code is not finished or implemented yet. Therfore, this code is not oporational or properly implemented yet.
        # ________________________________________________________
        create_purchases_table = """
            CREATE TABLE IF NOT EXISTS purchases (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                listing_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                purchase_price NUMERIC(10,2) NOT NULL CHECK (purchase_price >= 0),
                purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT fk_purchase_user
                    FOREIGN KEY(user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,

                CONSTRAINT fk_purchase_listing
                    FOREIGN KEY(listing_id)
                    REFERENCES listings(id)
                    ON DELETE CASCADE
            );
        """
        cur.execute(create_purchases_table)

        # ________________________________________________________
        # WISHLIST TABLE (User wishlists)
        # The frontend protion of this code is not finished or implemented yet. Therfore, this code is not oporational or properly implemented yet.
        # ________________________________________________________
        create_wishlist_table = """
            CREATE TABLE IF NOT EXISTS wishlist (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                listing_id INTEGER NOT NULL,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT fk_wishlist_user
                    FOREIGN KEY(user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,

                CONSTRAINT fk_wishlist_listing
                    FOREIGN KEY(listing_id)
                    REFERENCES listings(id)
                    ON DELETE CASCADE,

                CONSTRAINT unique_user_listing_wishlist
                    UNIQUE (user_id, listing_id)
            );
        """
        cur.execute(create_wishlist_table)

        # ________________________________________________________
        # RETURNS TABLE
        # Tracks return requests without hard deletion.
        # ________________________________________________________
        create_returns_table = """
            CREATE TABLE IF NOT EXISTS returns (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                order_number VARCHAR(120) NOT NULL,
                reason TEXT NOT NULL,
                has_damage BOOLEAN NOT NULL,
                damage_image_url TEXT,
                status VARCHAR(20) NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'reviewed', 'resolved')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_deleted BOOLEAN DEFAULT FALSE,

                CONSTRAINT fk_return_user
                    FOREIGN KEY(user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            );
        """
        cur.execute(create_returns_table)

        cur.execute("ALTER TABLE returns ADD COLUMN IF NOT EXISTS damage_image_url TEXT;")
        cur.execute("ALTER TABLE returns ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
        cur.execute("ALTER TABLE returns ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;")

        # ________________________________________________________
        # CART ITEMS TABLE (Persistent Bag)
        # ________________________________________________________
        create_cart_items_table = """
            CREATE TABLE IF NOT EXISTS cart_items (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                item_id INTEGER,
                item_name VARCHAR(255) NOT NULL,
                price NUMERIC(10,2) NOT NULL CHECK (price >= 0),
                quantity INTEGER NOT NULL DEFAULT 1,
                size VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT fk_cart_user
                    FOREIGN KEY(user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            );
        """
        cur.execute(create_cart_items_table)

        # ________________________________________________________
        # ORDERS TABLE (Checkout orders)
        # ________________________________________________________
        create_orders_table = """
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                confirmation_number VARCHAR(50) UNIQUE NOT NULL,
                buyer_first_name VARCHAR(100) NOT NULL,
                buyer_last_name VARCHAR(100) NOT NULL,
                buyer_email VARCHAR(255) NOT NULL,
                buyer_contact VARCHAR(100) NOT NULL,
                buyer_meeting_location TEXT NOT NULL,
                total_amount NUMERIC(10,2) NOT NULL,
                order_status VARCHAR(20) DEFAULT 'SUBMITTED',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT fk_order_user
                    FOREIGN KEY(user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            );
        """
        cur.execute(create_orders_table)

        # ________________________________________________________
        # ORDER ITEMS TABLE (Items per order)
        # ________________________________________________________
        create_order_items_table = """
            CREATE TABLE IF NOT EXISTS order_items (
                id SERIAL PRIMARY KEY,
                order_id INTEGER NOT NULL,
                listing_id INTEGER,
                item_name VARCHAR(255) NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                price_at_purchase NUMERIC(10,2) NOT NULL,
                selected_size VARCHAR(50),

                CONSTRAINT fk_order_item_order
                    FOREIGN KEY(order_id)
                    REFERENCES orders(id)
                    ON DELETE CASCADE
            );
        """
        cur.execute(create_order_items_table)

        # ________________________________________________________
        # TREASURE TOKENS: wallets, ledger, and order escrow
        # Added by Donovan Griffin, Iteration 3 - in-app token payment system.
        # 1 Treasure Token (TT) = $1.00 of listing price; no real money or card
        # data is ever handled. See docs/payment-tokens/README.md.
        # ________________________________________________________
        cur.execute("""
            CREATE TABLE IF NOT EXISTS wallets (
                user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                balance NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (balance >= 0),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS order_escrow (
                id SERIAL PRIMARY KEY,
                order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                buyer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                seller_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
                status VARCHAR(20) NOT NULL DEFAULT 'HELD'
                    CHECK (status IN ('HELD', 'RELEASED', 'REFUNDED', 'LOCKED')),
                code_nonce VARCHAR(64) NOT NULL,
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                UNIQUE (order_id, seller_id)
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS token_ledger (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                amount NUMERIC(12,2) NOT NULL CHECK (amount <> 0),
                entry_type VARCHAR(30) NOT NULL CHECK (entry_type IN
                    ('STARTING_BALANCE', 'ADMIN_GRANT', 'ESCROW_HOLD', 'ESCROW_RELEASE', 'ESCROW_REFUND')),
                order_id INTEGER REFERENCES orders(id) ON DELETE SET NULL,
                escrow_id INTEGER REFERENCES order_escrow(id) ON DELETE SET NULL,
                note TEXT,
                created_by VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_token_ledger_user ON token_ledger(user_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_order_escrow_seller ON order_escrow(seller_id, status);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_order_escrow_buyer ON order_escrow(buyer_id, status);")

        # messages table (new)
        create_messages_table = """
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                receiver_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                listing_id INTEGER REFERENCES listings(id) ON DELETE SET NULL,
                body TEXT NOT NULL,
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CHECK (sender_id <> receiver_id)
            );
        """
        cur.execute(create_messages_table)

        # reviews table (new)
        create_reviews_table = """
            CREATE TABLE IF NOT EXISTS reviews (
                id SERIAL PRIMARY KEY,
                storefront_id INTEGER NOT NULL REFERENCES storefronts(id) ON DELETE CASCADE,
                reviewer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                rating INTEGER NOT NULL CHECK (rating BETWEEN 1 and 5),
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (storefront_id, reviewer_id)
        );
        """
        cur.execute(create_reviews_table)

        conn.commit()

        print("DATABASE INITIALIZED: users, storefronts, listings, listing_images, listing_sizes, purchases, wishlist, orders, order_items, wallets, order_escrow, and token_ledger tables are ready.")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"SCHEMA ERROR: {e}")


if __name__ == "__main__":
    create_vault_tables()
