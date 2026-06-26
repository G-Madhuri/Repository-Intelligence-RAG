from abc import ABC, abstractmethod
from typing import Dict, Any, Type
from pydantic import BaseModel

class LLMClient(ABC):
    @abstractmethod
    def generate_json(
        self,
        prompt: str,
        response_schema: Type[BaseModel],
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        """Generates a structured JSON response matching the given response_schema."""
        pass

class GeminiLLMClient(LLMClient):
    def __init__(self, api_key: str):
        from google import genai
        self._client = genai.Client(api_key=api_key)

    def generate_json(
        self,
        prompt: str,
        response_schema: Type[BaseModel],
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        import json
        
        response = self._client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': response_schema,
                'temperature': temperature
            }
        )
        if not response.text:
            raise ValueError("Gemini returned empty response text.")
        return json.loads(response.text)
