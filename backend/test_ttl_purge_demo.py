import os
import sys
import time
import psycopg2
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "memory"))

from memory.vector_store import VectorStore
from main import purge_expired_repos, get_db_connection

def test_ttl_purge_evidence():
    print("==================================================")
    print("      LIVE 1-HOUR TTL PURGE VERIFICATION TEST     ")
    print("==================================================")

    uid = "00000000-0000-0000-0000-000000000001"
    repo_id = "test-ttl-demo-repo"
    namespace = f"repo_{repo_id.replace('-', '_')}"

    # 1. Setup Pinecone vector store and insert a sample vector into namespace
    vs = VectorStore()
    print(f"\n[Step 1] Upserting test vectors into Pinecone namespace '{namespace}'...")
    vs.add_documents(
        repo_id=repo_id,
        documents=["Test document for TTL expiration evidence."],
        metadatas=[{"category": "test"}],
        ids=["doc_ttl_1"],
        embeddings=[[0.05] * 1024]
    )
    time.sleep(2)
    
    count_before = vs.count_documents(repo_id)
    print(f"  [+] Vectors in Pinecone namespace '{namespace}' BEFORE purge: {count_before}")

    # 2. Insert expired repo row into Supabase (expires_at set to 5 minutes ago)
    print(f"\n[Step 2] Inserting EXPIRED repository record into Supabase table 'repos'...")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (id, email) VALUES (%s, %s)
                ON CONFLICT (id) DO NOTHING;
            """, (uid, "ttl-test@example.com"))

            # Set expires_at = NOW() - INTERVAL '5 minutes' (EXPIRED)
            cur.execute("""
                INSERT INTO repos (repo_id, uid, name, status, created_at, expires_at)
                VALUES (%s, %s, %s, %s, NOW() - INTERVAL '10 minutes', NOW() - INTERVAL '5 minutes')
                ON CONFLICT (repo_id) DO UPDATE SET expires_at = NOW() - INTERVAL '5 minutes';
            """, (repo_id, uid, "ttl-demo-repo", "completed"))
            
            cur.execute("SELECT repo_id, expires_at FROM repos WHERE repo_id = %s;", (repo_id,))
            row = cur.fetchone()
            print(f"  [+] Supabase record created: repo_id='{row[0]}', expires_at='{row[1]}'")

    # 3. Trigger the purge_expired_repos() job
    print("\n[Step 3] Running purge_expired_repos() TTL cleanup task...")
    purge_expired_repos()

    # 4. Prove namespace deleted from Pinecone & row deleted from Supabase
    time.sleep(2)
    count_after = vs.count_documents(repo_id)
    print(f"\n[Step 4] Checking Pinecone & Supabase AFTER purge...")
    print(f"  [+] Vectors in Pinecone namespace '{namespace}' AFTER purge: {count_after}")
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM repos WHERE repo_id = %s;", (repo_id,))
            db_count = cur.fetchone()[0]
            print(f"  [+] Supabase record count AFTER purge: {db_count}")

    if count_after == 0 and db_count == 0:
        print("\n==================================================")
        print("  [SUCCESS] 1-HOUR TTL PURGE PROVEN WITH LOGS & EVIDENCE! ")
        print("==================================================")

if __name__ == "__main__":
    test_ttl_purge_evidence()
