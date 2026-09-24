#By Ryan Grimes 2/2/2026
import sys
import os

# Ensure Python can see backend folder and subfolders
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.auth_services import AuthService
from config.db import get_connection

def test_registration():
    auth = AuthService() #Initalize the service layer

    conn = get_connection()

    if not conn:
        print("Could not connect to AWS RDS")
        return

    print("Attempting to register user...")

    try:
        success, message = auth.register_user(
            db_conn=conn,
            username="ahw", 
            password="SecurePassword123", 
            email="ahw@hamptonu.edu"
        )

        if success:
            print("\nThe Database is officially accepting users!")
            print(f"Message: {message}")
        else:
            print("\nRegistration failed")
            print(f"Reason: {message}")

    finally:
        conn.close()

if __name__ == "__main__":
    test_registration()