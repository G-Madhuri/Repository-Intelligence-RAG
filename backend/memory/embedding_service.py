import os
import logging
from typing import List, Optional

logger = logging.getLogger("embedding_service")

class EmbeddingService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Gemini API key is required to generate embeddings.")
        from google import genai
        self.client = genai.Client(api_key=self.api_key)

    def embed_text(self, text: str) -> List[float]:
        """Generates embedding for a single text string."""
        try:
            response = self.client.models.embed_content(
                model='text-embedding-004',
                contents=text
            )
            if response.embeddings and len(response.embeddings) > 0:
                return response.embeddings[0].values
            raise ValueError("No embeddings returned from Gemini API.")
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise e

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a batch list of text strings."""
        if not texts:
            return []
        try:
            # Check length to prevent massive batch issues; text-embedding-004 supports bulk
            response = self.client.models.embed_content(
                model='text-embedding-004',
                contents=texts
            )
            if response.embeddings and len(response.embeddings) == len(texts):
                return [e.values for e in response.embeddings]
            elif response.embeddings:
                return [e.values for e in response.embeddings]
            raise ValueError("No embeddings returned from batch API call.")
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise e
