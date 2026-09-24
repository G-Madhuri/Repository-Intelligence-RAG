import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("DATABASE_URL")
conn = psycopg2.connect(db_url)
conn.autocommit = True
cur = conn.cursor()

print("Auto-confirming all existing users in auth.users...")
cur.execute("UPDATE auth.users SET email_confirmed_at = NOW() WHERE email_confirmed_at IS NULL;")
print(f"[+] Updated {cur.rowcount} users to email_confirmed_at = NOW()")

print("\nCreating SQL auto-confirm trigger for future users...")
trigger_sql = """
CREATE OR REPLACE FUNCTION auto_confirm_user_email()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.email_confirmed_at IS NULL THEN
    NEW.email_confirmed_at := NOW();
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_auto_confirm ON auth.users;
CREATE TRIGGER on_auth_user_auto_confirm
  BEFORE INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION auto_confirm_user_email();
"""

cur.execute(trigger_sql)
print("[+] Created auto_confirm_user_email SQL trigger on auth.users successfully!")

conn.close()
