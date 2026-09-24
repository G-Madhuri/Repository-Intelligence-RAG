import os
import logging
from typing import List, Optional
from pinecone import Pinecone

logger = logging.getLogger("embedding_service")

class EmbeddingService:
    def __init__(self, api_key: Optional[str] = None, model_name: str = "llama-text-embed-v2"):
        self.pinecone_api_key = api_key or os.environ.get("PINECONE_API_KEY")
        self.model_name = model_name
        self.pc = None
        
        if self.pinecone_api_key:
            try:
                self.pc = Pinecone(api_key=self.pinecone_api_key)
                logger.info(f"Initialized EmbeddingService with Pinecone model '{self.model_name}'")
            except Exception as e:
                logger.warning(f"Could not initialize Pinecone client for embedding: {e}")

    def embed_text(self, text: str) -> List[float]:
        """Generates a 1024-dimension query embedding using llama-text-embed-v2."""
        if self.pc:
            try:
                res = self.pc.inference.embed(
                    model=self.model_name,
                    inputs=[text],
                    parameters={"input_type": "query", "truncate": "END"}
                )
                if res and len(res) > 0:
                    return res[0].values
            except Exception as e:
                logger.error(f"Error generating embedding with {self.model_name}: {e}")
        return []

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings in batch for passage texts using llama-text-embed-v2."""
        if not texts:
            return []
        if self.pc:
            try:
                # Batch in groups of 50
                batch_size = 50
                all_embeddings = []
                for start in range(0, len(texts), batch_size):
                    batch = texts[start:start + batch_size]
                    res = self.pc.inference.embed(
                        model=self.model_name,
                        inputs=batch,
                        parameters={"input_type": "passage", "truncate": "END"}
                    )
                    all_embeddings.extend([item.values for item in res])
                return all_embeddings
            except Exception as e:
                logger.error(f"Error generating batch embeddings with {self.model_name}: {e}")
        return []
