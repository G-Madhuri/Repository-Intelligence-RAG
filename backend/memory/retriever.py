import logging
from typing import List, Dict, Any, Optional
from memory.embedding_service import EmbeddingService
from memory.vector_store import VectorStore

logger = logging.getLogger("retriever")

class KnowledgeRetriever:
    def __init__(self, embedding_service: EmbeddingService, vector_store: VectorStore):
        self.embedder = embedding_service
        self.store = vector_store

    def retrieve(
        self,
        repo_id: str,
        query: str,
        top_k: int = 5,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Runs semantic search on ChromaDB for the repo using the query.
        Supports filtering by metadata 'category'.
        """
        logger.info(f"Retrieving context for repo {repo_id}, query: '{query}' (category filter: {category}, top_k: {top_k})")
        
        try:
            # Generate query vector using embedder
            query_embedding = self.embedder.embed_text(query)
            
            # Setup filter
            where_filter = None
            if category:
                where_filter = {"category": category}
                
            return self.store.query_documents(
                repo_id=repo_id,
                query_embedding=query_embedding,
                top_k=top_k,
                where_filter=where_filter
            )
        except Exception as e:
            logger.error(f"Failed to retrieve vector search results: {e}")
            return []
