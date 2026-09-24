# Created by Ryan Grimes on 4/12/2026
# Purpose: Simple integration test to verify login functionality against AWS RDS database.

import sys
import os

# Ensure Python can see backend folder and subfolders
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.auth_services import AuthService
from config.db import get_connection

def drive_login():
    auth = AuthService()
    conn = get_connection()

    if not conn:
        print("DRIVER ERROR: Could not connect to AWS RDS.")
        return

    print("Testing Login Validation Driver...")
    try:
        success, role = auth.validate_login("Testing67", "password", conn)

        if success:
            print(f"RESULT: Login verified. User Role: {role}")
        else:
            print(f"RESULT: Authentication Denied. Invalid credentials.")

    finally:
        conn.close()

if __name__ == "__main__":
    drive_login()