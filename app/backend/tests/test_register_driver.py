# Created by Ryan Grimes on 4/12/2026
# Purpose: Simple integration test to verify registration functionality against AWS RDS database.

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.auth_services import AuthService
from config.db import get_connection

def drive_registration():
    auth = AuthService()
    conn = get_connection()

    if not conn:
        print("Driver could not connect to AWS RDS.")
        return

    print("Testing Registration Driver...")
    try:
        success, message = auth.register_user(
            "Testing67", 
            "password", 
            "tester67@hamptonu.edu", 
            conn
        )

        if success:
            print(f"RESULT: Success! {message}")
        else:
            print(f"RESULT: Failed. Reason: {message}")

    finally:
        conn.close()

if __name__ == "__main__":
    drive_registration()