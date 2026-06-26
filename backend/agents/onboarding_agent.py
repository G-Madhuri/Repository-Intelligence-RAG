import json
from typing import Dict, Any
from agents.base_agent import BaseAgent, AgentResponseSchema

class OnboardingAgent(BaseAgent):
    async def run(
        self,
        profile: Dict[str, Any],
        graph: Dict[str, Any],
        summary: Dict[str, Any],
        report: str,
        query: str
    ) -> Dict[str, Any]:
        prompt = f"""
You are the Onboarding Agent. Your responsibility is to guide new developers in understanding the project execution flow, configuring local developer environments, locating entry point scripts, outlining recommended learning paths, and listing the key folders/files to read first.

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

Perform a rigorous developer-focused onboarding walkthrough to answer this query. Your citations must point out documentation, entry files, or configuration variables that speed up developer setup.
Return your structured answer matching the AgentResponseSchema.
"""
        return await self._call_llm_json(prompt, AgentResponseSchema)
