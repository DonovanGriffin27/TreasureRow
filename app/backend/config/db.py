#Initializes AWS RDS Credentials
#Updated 3/3/2026 by Ryan Grimes

import os #Allows files to manage files, see directory paths, and read environment
import logging
import psycopg2 #Allows for Python to manage PostgreSQL databases
from dotenv import load_dotenv #Loads the keys from the hidden .env file

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '../../.env'))

logger = logging.getLogger(__name__)

def get_connection():
    """Returns a new PostgreSQL connection, or None if the connection fails."""
    try:
        conn_kwargs = {
            "host": os.getenv('DB_HOST'), #The web address of the database server
            "dbname": os.getenv('DB_NAME'), #The name of the database
            "user": os.getenv('DB_USER'), #database login credentials
            "password": os.getenv('DB_PASSWORD'), #database login credentials
            "port": int(os.getenv('DB_PORT', 5432)),
        }

        sslmode = os.getenv("DB_SSLMODE")
        sslrootcert = os.getenv("DB_SSLROOTCERT")
        if sslmode:
            conn_kwargs["sslmode"] = sslmode
        if sslrootcert:
            conn_kwargs["sslrootcert"] = sslrootcert

        return psycopg2.connect(**conn_kwargs)

    except Exception as e:
        logger.error("Database connection error: %s", type(e).__name__)
        return None
