import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise ValueError("DATABASE_URL is not set.")

print("Connecting to Supabase PostgreSQL database to apply SQL migration...")
conn = psycopg2.connect(db_url)
conn.autocommit = True
cursor = conn.cursor()

migration_sql = """
-- Step 1: Create Tables
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY REFERENCES auth.users(id),
  email TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS repos (
  repo_id TEXT PRIMARY KEY,
  uid UUID REFERENCES users(id),
  name TEXT,
  status TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  expires_at TIMESTAMPTZ DEFAULT now() + INTERVAL '1 hour'
);

CREATE TABLE IF NOT EXISTS jobs (
  job_id TEXT PRIMARY KEY,
  repo_id TEXT REFERENCES repos(repo_id),
  uid UUID REFERENCES users(id),
  status TEXT,
  stage TEXT,
  progress INT DEFAULT 0,
  error TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  uid UUID REFERENCES users(id),
  repo_id TEXT,
  role TEXT,
  content TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Step 2: Enable Row Level Security (RLS)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE repos ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

-- Create RLS Policies
DROP POLICY IF EXISTS repos_user_policy ON repos;
CREATE POLICY repos_user_policy ON repos FOR ALL USING (uid = auth.uid());

DROP POLICY IF EXISTS jobs_user_policy ON jobs;
CREATE POLICY jobs_user_policy ON jobs FOR ALL USING (uid = auth.uid());

DROP POLICY IF EXISTS conversations_user_policy ON conversations;
CREATE POLICY conversations_user_policy ON conversations FOR ALL USING (uid = auth.uid());

DROP POLICY IF EXISTS users_user_policy ON users;
CREATE POLICY users_user_policy ON users FOR SELECT USING (id = auth.uid());
"""

cursor.execute(migration_sql)
print("[+] Supabase SQL migration executed successfully!")

# Verify table existence
cursor.execute("""
    SELECT table_name FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name IN ('users', 'repos', 'jobs', 'conversations');
""")
tables = cursor.fetchall()
print("\n[+] Created Public Tables:")
for t in tables:
    print(f"  - {t[0]}")

conn.close()
