#Initializes AWS RDS Credentials
#Updated 3/3/2026 by Ryan Grimes

import os #Allows files to manage files, see directory paths, and read environment
import psycopg2 #Allows for Python to manage PostgreSQL databases
from dotenv import load_dotenv #Loads the keys from the hidden .env file

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '../../.env'))

def get_connection():
    try: 
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'), #The web address of the database server
            database=os.getenv('DB_NAME'), #The name of the database
            user=os.getenv('DB_USER'), #database login credentials
            password=os.getenv('DB_PASSWORD'), #database login credentials
            port=os.getenv('DB_PORT')
        )

        print("Login Logic: Connected to AWS RDS")
        return conn

    except Exception as e:
        print(f"Login Logic: Connection Error: {e}")
        return None