from tools.base_tool import BaseTool
from services.repositoryMemory import memory_service
from typing import Any

class GraphQueryTool(BaseTool):
    @property
    def name(self) -> str:
        return "graph_query"

    @property
    def description(self) -> str:
        return "Queries the repository code dependency graph, entry points, workflows, and concepts. Inputs: repo_id (str)."

    def execute(self, **kwargs) -> Any:
        repo_id = kwargs.get("repo_id")
        if not repo_id:
            return {"error": "Missing required parameter: repo_id."}
            
        data = memory_service.retrieve(repo_id)
        if not data or "graph" not in data:
            return {"error": f"No architecture graph found for repository {repo_id}."}
            
        graph = data["graph"]
        return {
            "entry_points": graph.get("entry_points", []),
            "business_flows": graph.get("business_flows", []),
            "critical_paths": graph.get("critical_paths", []),
            "concepts": graph.get("concepts", []),
            "node_count": len(graph.get("nodes", [])),
            "edge_count": len(graph.get("edges", []))
        }
