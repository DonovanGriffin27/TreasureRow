import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    """
    Creates and returns a new PostgreSQL connection
    using environment variables.
    Supports AWS RDS SSL configuration if provided.

    This is the single place the app opens database connections;
    config/db.py and init_db.py call it too. - Donovan Griffin, Iteration 3
    """

    conn_kwargs = {
        "host": os.getenv("DB_HOST"),
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "port": int(os.getenv("DB_PORT", 5432)),
        # fail fast instead of hanging for ~75s when the database is
        # unreachable (e.g. IP not allowed in the RDS security group)
        "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", 5)),
    }

    sslmode = os.getenv("DB_SSLMODE")
    sslrootcert = os.getenv("DB_SSLROOTCERT")

    if sslmode:
        conn_kwargs["sslmode"] = sslmode

    if sslrootcert:
        conn_kwargs["sslrootcert"] = sslrootcert

    return psycopg2.connect(**conn_kwargs)
