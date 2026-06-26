import json
from typing import Dict, Any
from agents.base_agent import BaseAgent, AgentResponseSchema

class QualityAgent(BaseAgent):
    async def run(
        self,
        profile: Dict[str, Any],
        graph: Dict[str, Any],
        summary: Dict[str, Any],
        report: str,
        query: str
    ) -> Dict[str, Any]:
        prompt = f"""
You are the Quality Agent. Your responsibility is to analyze the codebase for code quality, maintainability, architectural complexity, indicators of dead code, large/bloated modules, potential code smells, and testing/coverage strategies.

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

Perform a rigorous analysis of the code quality and maintainability indicators to answer this query. Your citations must specify modules or files containing smells, complex blocks, or missing test configurations.
Return your structured answer matching the AgentResponseSchema.
"""
        return await self._call_llm_json(prompt, AgentResponseSchema)
