from tools.base_tool import BaseTool
from services.repositoryMemory import memory_service
from typing import Any

class ApiLookupTool(BaseTool):
    @property
    def name(self) -> str:
        return "api_lookup"

    @property
    def description(self) -> str:
        return "Queries project HTTP routes, api endpoints, and controllers. Inputs: repo_id (str)."

    def execute(self, **kwargs) -> Any:
        repo_id = kwargs.get("repo_id")
        if not repo_id:
            return {"error": "Missing required parameter: repo_id."}
            
        data = memory_service.retrieve(repo_id)
        if not data or "profile" not in data:
            return {"error": f"No profile found for repository {repo_id}."}
            
        profile = data["profile"]
        return {
            "api_endpoints": profile.get("api_endpoints", []),
            "authentication_methods": profile.get("authentication_methods", [])
        }
