import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Type
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

logger = logging.getLogger("llm_client")

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
        self.api_key = api_key
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0.2
        )

    def generate_json(
        self,
        prompt: str,
        response_schema: Type[BaseModel],
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        """Generates structured Pydantic / JSON output using LangChain ChatGoogleGenerativeAI."""
        try:
            structured_llm = self.llm.with_structured_output(response_schema)
            result = structured_llm.invoke([HumanMessage(content=prompt)])
            if isinstance(result, BaseModel):
                return result.model_dump()
            elif isinstance(result, dict):
                return result
            else:
                raise ValueError(f"Unexpected response type from structured LLM: {type(result)}")
        except Exception as e:
            logger.error(f"Error in GeminiLLMClient LangChain generation: {e}")
            raise e
