import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from agents.llm_client import LLMClient

class SynthesizedResponse(BaseModel):
    summary: str = Field(description="A concise summary of all findings across agents")
    detailed_explanation: str = Field(description="A comprehensive, detailed markdown explanation combining all insights, resolving duplicates, and directly answering the user query")
    agent_contributions: List[str] = Field(description="List of strings explaining what each agent contributed (e.g. 'SecurityAgent: identified lack of rate limiting on the login route.')")
    confidence_score: float = Field(description="A combined confidence score representing the quality and consensus of the generated answer (0.0 to 1.0)")

class ResponseSynthesizer:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    async def synthesize(
        self,
        query: str,
        agent_responses: List[Dict[str, Any]],
        memory_context: Optional[str] = None,
        search_results: Optional[List[Dict[str, Any]]] = None,
        tool_outputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        import asyncio
        responses_str = json.dumps(agent_responses, indent=2)
        
        context_parts = []
        if memory_context:
            context_parts.append(f"--- Past Conversation turns ---\n{memory_context}")
        if search_results:
            search_text = "\n\n".join(
                f"[Search similarity={r['similarity']:.2f}]\n{r['content']}"
                for r in search_results
            )
            context_parts.append(f"--- Semantic Search Context ---\n{search_text}")
        if tool_outputs:
            tools_text = json.dumps(tool_outputs, indent=2)
            context_parts.append(f"--- Direct Tool Outputs ---\n{tools_text}")
            
        extra_context = "\n\n".join(context_parts)
        
        prompt = f"""
You are the Principal Systems Integrator and Response Synthesizer.
Your goal is to digest all specialized agent reports, retrieve context, tool outputs, and compile them into a single, cohesive, premium response answering the user's query.

User Query:
{query}

{extra_context}

Specialized Agent Responses:
{responses_str}

Tasks:
1. Synthesize a single coherent, authoritative detailed explanation in markdown.
2. Merge duplicate findings.
3. Call out specific contributions or viewpoints of the agents/tools.
4. Calculate an overall confidence score based on individual agent confidence levels, tool relevance, and consensus.
5. Create a concise summary.

Return the result matching the schema in structured JSON format.
"""
        return await asyncio.to_thread(self.llm_client.generate_json, prompt, SynthesizedResponse, 0.2)
