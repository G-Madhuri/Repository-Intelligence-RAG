import json
from typing import Dict, Any
from agents.base_agent import BaseAgent, AgentResponseSchema

class DependencyAgent(BaseAgent):
    async def run(
        self,
        profile: Dict[str, Any],
        graph: Dict[str, Any],
        summary: Dict[str, Any],
        report: str,
        query: str
    ) -> Dict[str, Any]:
        prompt = f"""
You are the Dependency Agent. Your responsibility is to analyze libraries, package configurations (e.g. package.json, requirements.txt), framework selections, database integrations, cloud stack, and deployment environment setups.

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

Perform a rigorous analysis of project dependencies and frameworks to answer this query. Your citations must reference the package manifest files or configurations (e.g., "requirements.txt:L3", "docker-compose.yml:L5").
Return your structured answer matching the AgentResponseSchema.
"""
        return await self._call_llm_json(prompt, AgentResponseSchema)
