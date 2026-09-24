#By Ryan 2/27/2026
import psycopg2
import os
from dotenv import load_dotenv

env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
load_dotenv(env_path)

host = os.getenv('DB_HOST')
if not host:
    print(".env file not found at {env_path}")

try:
    # Attempt to "knock on the door" of the RDS server
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT')
    )
    print("SUCCESS: Your laptop is authorized. You have access to The Vault!")
    conn.close()
except Exception as e:
    print(f"CONNECTION FAILED: {e}")
