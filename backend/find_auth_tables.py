import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("DATABASE_URL")
conn = psycopg2.connect(db_url)
conn.autocommit = True
cur = conn.cursor()

cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'auth';")
tables = cur.fetchall()
print("Auth tables:")
for t in tables:
    print(f"  {t[0]}")

conn.close()
