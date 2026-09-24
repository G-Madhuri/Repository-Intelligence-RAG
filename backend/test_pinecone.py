import os
from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()

api_key = os.getenv("PINECONE_API_KEY")
index_name = os.getenv("PINECONE_INDEX_NAME")
host = os.getenv("PINECONE_HOST")

print(f"Connecting to Pinecone index '{index_name}'...")
pc = Pinecone(api_key=api_key)

index_description = pc.describe_index(index_name)
print("Index Details:")
print(f"  Name: {index_description.name}")
print(f"  Dimension: {index_description.dimension}")
print(f"  Metric: {index_description.metric}")
print(f"  Host: {index_description.host}")
if hasattr(index_description, 'embed') and index_description.embed:
    print(f"  Integrated Model: {index_description.embed}")

index = pc.Index(name=index_name)
stats = index.describe_index_stats()
print("\nIndex Stats:")
print(f"  Total Record Count: {stats.total_vector_count}")
print(f"  Namespaces: {stats.namespaces}")
