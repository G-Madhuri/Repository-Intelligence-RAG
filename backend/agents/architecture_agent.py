import json
from typing import Dict, Any
from agents.base_agent import BaseAgent, AgentResponseSchema

class ArchitectureAgent(BaseAgent):
    async def run(
        self,
        profile: Dict[str, Any],
        graph: Dict[str, Any],
        summary: Dict[str, Any],
        report: str,
        query: str
    ) -> Dict[str, Any]:
        prompt = f"""
You are the Architecture Agent. Your responsibility is to analyze the codebase structure, architectural design patterns, component relationships, data flow, business workflows, and entry points to answer the user query.

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

Perform a rigorous architectural analysis to answer this query. Your citations must specify files, code blocks, or components (e.g. "backend/main.py:L10-L40", "Graph Node: App.jsx").
Return your structured answer matching the AgentResponseSchema.
"""
        return await self._call_llm_json(prompt, AgentResponseSchema)
