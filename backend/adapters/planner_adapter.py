import time
from typing import Dict, Any
from agents.planner_agent import PlannerAgent

class ADKPlannerAdapter:
    """
    Adapter wrapping the PlannerAgent to match ADK planner expectations.
    """
    def __init__(self, planner: PlannerAgent):
        self.planner = planner

    async def create_plan(self, context: Dict[str, Any], query: str) -> Dict[str, Any]:
        profile = context.get("profile", {})
        graph = context.get("graph", {})
        summary = context.get("summary", {})
        report = context.get("report", "")
        
        # Call planner
        plan = await self.planner.run(
            profile=profile,
            graph=graph,
            summary=summary,
            report=report,
            query=query
        )
        return {
            "plan_id": f"plan_{int(time.time())}",
            "steps": [
                {
                    "stage": idx + 1,
                    "agents": stage,
                    "parameters": {"query": query}
                }
                for idx, stage in enumerate(plan.get("execution_order", []))
            ],
            "reasoning": plan.get("reasoning", ""),
            "selected_agents": plan.get("selected_agents", [])
        }
