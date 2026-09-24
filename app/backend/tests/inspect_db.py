import sys
import os

# Add backend folder to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db import get_connection

conn = get_connection()
cur = conn.cursor()

# Show all tables
cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
""")

tables = cur.fetchall()
print("Tables:")
for table in tables:
    print("-", table[0])

print("\n---\n")

# Show columns for each table
for table in tables:
    table_name = table[0]

    print(f"Columns in {table_name}:")

    cur.execute(f"""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = '{table_name}'
    """)

    columns = cur.fetchall()

    for col in columns:
        print("  -", col[0])

    print()

cur.close()
conn.close()