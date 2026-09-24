# Created by Ryan Grimes on 4/12/2026
# Purpose: Simple integration test to verify connectivity to AWS RDS database.

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.db import get_connection

def drive_db_test():
    print("Testing Database Connection Driver...")
    conn = get_connection()

    if conn:
        try:
            cur = conn.cursor()
            # Verify the users table is reachable
            cur.execute("SELECT COUNT(*) FROM users;")
            count = cur.fetchone()[0]
            
            print("CONNECTION STATUS: SUCCESS")
            print(f"AWS RDS STATUS: Online")
            print(f"TOTAL USERS IN DATABASE: {count}")
            
            cur.close()
        except Exception as e:
            print(f"DATABASE ERROR: {e}")
        finally:
            conn.close()
    else:
        print("CONNECTION STATUS: FAILED")

if __name__ == "__main__":
    drive_db_test()