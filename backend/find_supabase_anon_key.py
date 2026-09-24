import os
import jwt
import psycopg2
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("DATABASE_URL")
conn = psycopg2.connect(db_url)
conn.autocommit = True
cur = conn.cursor()

try:
    cur.execute("SELECT name, setting FROM pg_settings WHERE name LIKE '%jwt%' OR name LIKE '%secret%';")
    rows = cur.fetchall()
    print("Found settings:")
    for r in rows:
        print(f"  {r[0]} = {r[1]}")
except Exception as e:
    print(f"Error: {e}")

try:
    cur.execute("SELECT * FROM vault.decrypted_secrets;")
    rows = cur.fetchall()
    print("Vault secrets:")
    for r in rows:
        print(r)
except Exception as e:
    print(f"Vault error: {e}")

conn.close()
