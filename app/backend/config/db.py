#Initializes AWS RDS Credentials

import os #Allows files to manage files, see directory paths, and read environment
from dotenv import load_dotenv #Loads the keys from the hidden .env file

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '../../.env'))

def get_connection():
    # Uses the shared connection settings in backend/db.py (SSL + connect
    # timeout) so login and the rest of the app connect the same way.
    # Still returns None on failure, which the login/signup routes check for.
    # Updated by Donovan Griffin, Iteration 3
    from db import get_connection as connect

    # removed the "Connected to AWS RDS" print - it ran on every request, even on a
    # local database, and filled the app window - Jonah Goodwine, Iteration 4
    try:
        return connect()

    except Exception as e:
        print(f"[db] Connection error: {e}")
        return None
