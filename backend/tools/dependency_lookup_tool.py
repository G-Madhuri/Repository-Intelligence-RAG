from tools.base_tool import BaseTool
from services.repositoryMemory import memory_service
from typing import Any

class DependencyLookupTool(BaseTool):
    @property
    def name(self) -> str:
        return "dependency_lookup"

    @property
    def description(self) -> str:
        return "Queries libraries, dependencies, package configurations, and stack components. Inputs: repo_id (str)."

    def execute(self, **kwargs) -> Any:
        repo_id = kwargs.get("repo_id")
        if not repo_id:
            return {"error": "Missing required parameter: repo_id."}
            
        data = memory_service.retrieve(repo_id)
        if not data or "profile" not in data:
            return {"error": f"No profile found for repository {repo_id}."}
            
        profile = data["profile"]
        return {
            "languages": profile.get("languages", []),
            "frameworks": profile.get("frameworks", []),
            "databases": profile.get("databases", []),
            "dependencies": profile.get("dependencies", []),
            "project_type": profile.get("project_type", "")
        }
