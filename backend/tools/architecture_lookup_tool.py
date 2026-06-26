from tools.base_tool import BaseTool
from services.repositoryMemory import memory_service
from typing import Any

class ArchitectureLookupTool(BaseTool):
    @property
    def name(self) -> str:
        return "architecture_lookup"

    @property
    def description(self) -> str:
        return "Queries project high-level architecture pattern and main folders/modules. Inputs: repo_id (str)."

    def execute(self, **kwargs) -> Any:
        repo_id = kwargs.get("repo_id")
        if not repo_id:
            return {"error": "Missing required parameter: repo_id."}
            
        data = memory_service.retrieve(repo_id)
        if not data or "profile" not in data:
            return {"error": f"No intelligence profile found for repository {repo_id}."}
            
        profile = data["profile"]
        return {
            "architecture_pattern": profile.get("architecture_pattern", ""),
            "major_modules": profile.get("major_modules", []),
            "important_files": profile.get("important_files", [])
        }
