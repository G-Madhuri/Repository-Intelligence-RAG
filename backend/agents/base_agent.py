from abc import ABC, abstractmethod
from typing import Dict, Any, List
import asyncio
from pydantic import BaseModel, Field
from agents.llm_client import LLMClient

class AgentResponseSchema(BaseModel):
    agent: str = Field(description="Name of the agent, e.g., SecurityAgent")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0 based on relevance and sufficiency of data")
    answer: str = Field(description="Detailed answer or analysis regarding the user query")
    citations: List[str] = Field(description="Source files, line numbers, or endpoints cited as reference")
    reasoning: List[str] = Field(description="Step-by-step reasoning steps the agent took")

class BaseAgent(ABC):
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    @abstractmethod
    async def run(
        self,
        profile: Dict[str, Any],
        graph: Dict[str, Any],
        summary: Dict[str, Any],
        report: str,
        query: str
    ) -> Dict[str, Any]:
        """Runs the agent's analysis."""
        pass

    async def _call_llm_json(self, prompt: str, schema: Any, temperature: float = 0.2) -> Dict[str, Any]:
        return await asyncio.to_thread(self.llm_client.generate_json, prompt, schema, temperature)
