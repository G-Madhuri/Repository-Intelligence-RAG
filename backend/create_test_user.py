import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("DATABASE_URL")
conn = psycopg2.connect(db_url)
conn.autocommit = True
cur = conn.cursor()

# Insert dummy user into auth.users if not present
cur.execute("""
    INSERT INTO auth.users (id, instance_id, email, encrypted_password, email_confirmed_at, created_at, updated_at, role, aud)
    VALUES (
        '00000000-0000-0000-0000-000000000001',
        '00000000-0000-0000-0000-000000000000',
        'ttl-test@example.com',
        'dummy_password_hash',
        now(),
        now(),
        now(),
        'authenticated',
        'authenticated'
    ) ON CONFLICT (id) DO NOTHING;
""")
print("[+] Test user inserted into auth.users successfully!")
conn.close()
