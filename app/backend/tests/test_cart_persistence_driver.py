# Created by Ryan Grimes on 4/12/2026
# Purpose: Simple integration test to verify cart persistence functionality against AWS RDS database.

import sys
import os

# Add the project root to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.auth_services import AuthService
from config.db import get_connection

def print_cart_state(label, cart_items):
    if not cart_items:
        print("Items in cart: [Empty]")
    else:
        for item in cart_items:
            print(f"Item in cart: {item['name']} | Size: {item['size']} | Price: ${item['price']}")

def run_cart_test(target_username):
    service = AuthService()
    conn = get_connection()
    
    if not conn:
        print("FAILED: Could not connect to AWS RDS.")
        return

    try:
        cur = conn.cursor()
        
        # LOOKUP: Finding the user_id by username
        print(f"Searching database for user: '{target_username}'...")
        cur.execute("SELECT id FROM users WHERE username = %s", (target_username,))
        row = cur.fetchone()
        
        if not row:
            print(f"FAILED: No user found with the username '{target_username}'. Check your spelling!")
            return
            
        user_id = row[0]
        print(f"Username: {target_username} has User ID: {user_id}")
        print(f"Starting cart functionality test for {target_username} (ID: {user_id})")

        # PRE-TEST STATE
        print_cart_state("Initial state (Before Step 1)", service.get_user_cart(conn, user_id))

        # STEP 1: Clear Cart
        print("\nStep 1: Clearing existing cart items...")
        service.clear_user_cart(conn, user_id)
        print_cart_state("State after step 1 (Clear)", service.get_user_cart(conn, user_id))

        # STEP 2: Add Items
        print("\nStep 2: Adding test item to RDS...")
        cur.execute("""
            INSERT INTO cart_items (user_id, item_id, item_name, price, quantity, size)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, 101, 'Hampton Legacy Hoodie', 45.00, 1, 'L'))
        conn.commit()
        print_cart_state("State after step 2 (Add)", service.get_user_cart(conn, user_id))

        # STEP 3: Verify Persistence
        print("\nStep 3: Verifying persistence...")
        recovered_cart = service.get_user_cart(conn, user_id)
        print_cart_state("State after step 3 (Verification)", recovered_cart)

        # STEP 4: Removal
        print("\nStep 4: Testing removal of specific item...")
        cur.execute("DELETE FROM cart_items WHERE user_id = %s AND item_id = 101", (user_id,))
        conn.commit()
        print_cart_state("State after step 4 (Removal)", service.get_user_cart(conn, user_id))

    except Exception as e:
        print(f"Error during testing: {e}")
    finally:
        cur.close()
        conn.close()
        print("\n--- Test Complete ---")

if __name__ == "__main__":
    # Change this to the username you want to test
    run_cart_test("johncena")