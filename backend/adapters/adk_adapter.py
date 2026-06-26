from typing import Dict, Any
from adapters.agent_adapter import ADKAgentAdapter
from adapters.planner_adapter import ADKPlannerAdapter

class GoogleADKPlatformAdapter:
    """
    High-level adapter class representing a Google ADK Application context.
    Integrates the multi-agent layers and provides entry points for task execution.
    """
    def __init__(self, orchestrator: Any):
        self.orchestrator = orchestrator
        self.planner_adapter = ADKPlannerAdapter(orchestrator.planner)
        self.agent_adapters = {
            name: ADKAgentAdapter(agent)
            for name, agent in orchestrator.agents.items()
        }

    async def dispatch_query(
        self,
        profile: Dict[str, Any],
        graph: Dict[str, Any],
        summary: Dict[str, Any],
        report: str,
        query: str
    ) -> Dict[str, Any]:
        """
        Executes queries by forwarding them to the underlying orchestrator,
        representing a standard ADK execution cycle.
        """
        return await self.orchestrator.execute(
            profile=profile,
            graph=graph,
            summary=summary,
            report=report,
            query=query
        )
