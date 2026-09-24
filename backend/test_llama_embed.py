import os
from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()

api_key = os.getenv("PINECONE_API_KEY")
pc = Pinecone(api_key=api_key)

print("Testing Pinecone inference with model 'llama-text-embed-v2'...")
try:
    res = pc.inference.embed(
        model="llama-text-embed-v2",
        inputs=["What is Pinecone integrated inference with llama-text-embed-v2?"],
        parameters={"input_type": "query", "truncate": "END"}
    )
    embedding = res[0].values
    print(f"[+] Successfully generated embedding using llama-text-embed-v2!")
    print(f"    Embedding dimension: {len(embedding)}")
except Exception as e:
    print(f"[!] Error: {e}")
