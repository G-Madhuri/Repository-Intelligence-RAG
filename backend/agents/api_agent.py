import json
from typing import Dict, Any
from agents.base_agent import BaseAgent, AgentResponseSchema

class ApiAgent(BaseAgent):
    async def run(
        self,
        profile: Dict[str, Any],
        graph: Dict[str, Any],
        summary: Dict[str, Any],
        report: str,
        query: str
    ) -> Dict[str, Any]:
        prompt = f"""
You are the API Agent. Your responsibility is to analyze the API design of the repository, including HTTP methods, routes/endpoints, payload structures, external API dependencies, and data exchange/request-response flow.

Here is the repository context:
1. Profile:
{json.dumps(profile, indent=2)}
2. Graph Structure:
{json.dumps(graph, indent=2)}
3. Summary:
{json.dumps(summary, indent=2)}
4. Intelligence Report:
{report}

User Query:
{query}

Perform a rigorous analysis of the endpoints and API flow to answer this query. Your citations must specify specific routes or lines where endpoints are declared or configured.
Return your structured answer matching the AgentResponseSchema.
"""
        return await self._call_llm_json(prompt, AgentResponseSchema)
