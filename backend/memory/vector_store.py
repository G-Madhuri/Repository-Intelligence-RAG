import os
import logging
from typing import Dict, Any, List, Optional
from pinecone import Pinecone

logger = logging.getLogger("vector_store")

class VectorStore:
    def __init__(self, api_key: Optional[str] = None, index_name: Optional[str] = None):
        self.api_key = api_key or os.environ.get("PINECONE_API_KEY")
        self.index_name = index_name or os.environ.get("PINECONE_INDEX_NAME", "discord-agent-knowledge")
        
        if not self.api_key:
            raise ValueError("Pinecone API key is required.")
            
        self.pc = Pinecone(api_key=self.api_key)
        self.index = self.pc.Index(name=self.index_name)
        logger.info(f"Initialized Pinecone Vector Store for index: '{self.index_name}'")

    def get_namespace(self, repo_id: str) -> str:
        """Generates a clean namespace identifier per repository."""
        return f"repo_{repo_id.replace('-', '_')}"

    def add_documents(
        self,
        repo_id: str,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
        embeddings: Optional[List[List[float]]] = None
    ):
        """
        Upserts documents into Pinecone within the repository namespace.
        Supports dense embeddings array or raw text records using Pinecone integrated inference.
        """
        if not documents:
            return
            
        namespace = self.get_namespace(repo_id)
        vectors = []
        
        for i, (doc, meta, doc_id) in enumerate(zip(documents, metadatas, ids)):
            meta_copy = dict(meta) if meta else {}
            meta_copy["text"] = doc  # Store original text in metadata field
            
            if embeddings and i < len(embeddings) and embeddings[i]:
                vectors.append({
                    "id": doc_id,
                    "values": embeddings[i],
                    "metadata": meta_copy
                })
            else:
                # If no embedding array provided, format record for Pinecone integrated inference
                vectors.append({
                    "id": doc_id,
                    "metadata": meta_copy
                })
                
        # Batch upsert in chunks of 50 to respect Pinecone record limit (max 96)
        batch_size = 50
        for start in range(0, len(vectors), batch_size):
            batch = vectors[start:start + batch_size]
            if batch and "values" in batch[0]:
                self.index.upsert(vectors=batch, namespace=namespace)
            elif batch:
                self.index.upsert_records(namespace=namespace, records=batch)
                
        logger.info(f"Upserted {len(documents)} document chunks to Pinecone namespace '{namespace}'")


    def query_documents(
        self,
        repo_id: str,
        query_embedding: Optional[List[float]] = None,
        query_text: Optional[str] = None,
        top_k: int = 5,
        where_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Queries Pinecone using either dense query vector or raw query text."""
        namespace = self.get_namespace(repo_id)
        
        filter_dict = where_filter if where_filter else None
        
        if query_embedding:
            res = self.index.query(
                namespace=namespace,
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter_dict
            )
        elif query_text:
            # Query using Pinecone integrated inference search if query text is provided
            res = self.index.search(
                namespace=namespace,
                query={"top_k": top_k, "inputs": {"text": query_text}},
                fields=["text", "category", "path"],
                filter=filter_dict
            )
        else:
            raise ValueError("Must provide either query_embedding or query_text.")
            
        formatted = []
        matches = getattr(res, "matches", []) or res.get("matches", [])
        
        for match in matches:
            m_dict = match if isinstance(match, dict) else match.to_dict()
            metadata = m_dict.get("metadata", {})
            doc_content = metadata.get("text", "")
            score = round(float(m_dict.get("score", 0.0)), 4)
            
            formatted.append({
                "id": m_dict.get("id", ""),
                "content": doc_content,
                "metadata": metadata,
                "similarity": score,
                "distance": round(1.0 - score, 4)
            })
            
        formatted.sort(key=lambda x: x["similarity"], reverse=True)
        return formatted

    def delete_collection(self, repo_id: str):
        namespace = self.get_namespace(repo_id)
        try:
            self.index.delete(delete_all=True, namespace=namespace)
            logger.info(f"Deleted Pinecone namespace: {namespace}")
        except Exception as e:
            logger.warning(f"Could not delete namespace {namespace}: {e}")

    def count_documents(self, repo_id: str) -> int:
        namespace = self.get_namespace(repo_id)
        try:
            stats = self.index.describe_index_stats()
            ns_stats = stats.namespaces.get(namespace, {})
            return ns_stats.get("vector_count", 0) if isinstance(ns_stats, dict) else getattr(ns_stats, "vector_count", 0)
        except Exception:
            return 0
