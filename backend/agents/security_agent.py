import json
from typing import Dict, Any
from agents.base_agent import BaseAgent, AgentResponseSchema

class SecurityAgent(BaseAgent):
    async def run(
        self,
        profile: Dict[str, Any],
        graph: Dict[str, Any],
        summary: Dict[str, Any],
        report: str,
        query: str
    ) -> Dict[str, Any]:
        prompt = f"""
You are the Security Agent. Your responsibility is to analyze the codebase for authentication methods, authorization mechanisms, handling of secrets/API keys, safety vulnerabilities, unsafe coding practices, and package dependencies that pose risks.

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

Perform a rigorous security analysis to answer this query. Your citations must specify files, lines, or configurations where security measures are implemented, missing, or potentially vulnerable.
Return your structured answer matching the AgentResponseSchema.
"""
        return await self._call_llm_json(prompt, AgentResponseSchema)
