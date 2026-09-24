import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

db_url = os.getenv("DATABASE_URL")
print("Testing Supabase PostgreSQL connection...")
try:
    conn = psycopg2.connect(db_url, connect_timeout=5)
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    db_version = cursor.fetchone()
    print("[+] Successfully connected to Supabase PostgreSQL!")
    print(f"    PostgreSQL Version: {db_version[0]}")
    conn.close()
except Exception as e:
    print(f"[!] Supabase connection failed: {e}")
