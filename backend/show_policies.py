import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("DATABASE_URL")
conn = psycopg2.connect(db_url)
cur = conn.cursor()

cur.execute("""
    SELECT tablename, policyname, cmd, qual 
    FROM pg_policies 
    WHERE schemaname = 'public'
    ORDER BY tablename, policyname;
""")
rows = cur.fetchall()

print("==========================================================")
print("              SUPABASE PUBLIC RLS POLICIES                ")
print("==========================================================")
print(f"{'TABLENAME':<15} | {'POLICYNAME':<25} | {'CMD':<8} | {'QUAL / USING EXPRESSION'}")
print("-" * 80)
for r in rows:
    print(f"{r[0]:<15} | {r[1]:<25} | {r[2]:<8} | {r[3]}")
print("==========================================================")

conn.close()
