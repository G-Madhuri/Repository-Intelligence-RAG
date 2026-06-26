from typing import Dict, Any
from agents.base_agent import BaseAgent

class ADKAgentAdapter:
    """
    Adapter wrapping existing BaseAgent specialized agents to conform to Google ADK
    agent invocation schemas.
    """
    def __init__(self, agent: BaseAgent):
        self.agent = agent
        self.name = agent.__class__.__name__

    async def execute_task(self, context: Dict[str, Any], query: str) -> Dict[str, Any]:
        profile = context.get("profile", {})
        graph = context.get("graph", {})
        summary = context.get("summary", {})
        report = context.get("report", "")
        
        # Call the underlying agent
        return await self.agent.run(
            profile=profile,
            graph=graph,
            summary=summary,
            report=report,
            query=query
        )
