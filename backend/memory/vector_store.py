import os
import logging
from typing import Dict, Any, List, Optional
import chromadb

logger = logging.getLogger("vector_store")

class VectorStore:
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or os.environ.get("CHROMA_DB_PATH", "./chroma_db")
        os.makedirs(self.storage_path, exist_ok=True)
        # Initialize persistent ChromaDB client
        self.client = chromadb.PersistentClient(path=self.storage_path)

    def get_collection(self, repo_id: str):
        # Convert UUID repo_id to a valid Chroma collection name (alphanumeric and underscores)
        coll_name = f"repo_{repo_id.replace('-', '_')}"
        return self.client.get_or_create_collection(
            name=coll_name,
            metadata={"hnsw:space": "cosine"}
        )

    def add_documents(
        self,
        repo_id: str,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
        embeddings: List[List[float]]
    ):
        """Adds documents with their corresponding embeddings and metadata."""
        if not documents:
            return
        collection = self.get_collection(repo_id)
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings
        )
        logger.info(f"Added {len(documents)} chunks to vector store collection for repo {repo_id}")

    def query_documents(
        self,
        repo_id: str,
        query_embedding: List[float],
        top_k: int = 5,
        where_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Queries ChromaDB using the query vector, returning matching chunks with similarity scores."""
        collection = self.get_collection(repo_id)
        
        # Query ChromaDB
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter
        )
        
        formatted = []
        if results and "documents" in results and len(results["documents"]) > 0:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results.get("metadatas") else [{} for _ in range(len(docs))]
            ids = results["ids"][0] if results.get("ids") else [str(i) for i in range(len(docs))]
            distances = results["distances"][0] if results.get("distances") else [0.0 for _ in range(len(docs))]
            
            for doc, meta, doc_id, dist in zip(docs, metas, ids, distances):
                # Cosine distance to similarity: 1 - distance
                similarity = 1.0 - dist
                formatted.append({
                    "id": doc_id,
                    "content": doc,
                    "metadata": meta,
                    "similarity": round(similarity, 4),
                    "distance": round(dist, 4)
                })
        
        # Sort by similarity descending
        formatted.sort(key=lambda x: x["similarity"], reverse=True)
        return formatted

    def delete_collection(self, repo_id: str):
        coll_name = f"repo_{repo_id.replace('-', '_')}"
        try:
            self.client.delete_collection(name=coll_name)
            logger.info(f"Deleted vector store collection: {coll_name}")
        except Exception as e:
            logger.warning(f"Could not delete collection {coll_name}: {e}")

    def count_documents(self, repo_id: str) -> int:
        try:
            collection = self.get_collection(repo_id)
            return collection.count()
        except Exception:
            return 0
