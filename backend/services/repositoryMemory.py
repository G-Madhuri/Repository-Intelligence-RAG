import os
import json
from typing import Dict, Any, Optional

class RepositoryMemoryService:
    """
    Foundational data and memory layer for repository intelligence.
    Manages in-memory caching with disk persistence for structured
    artifacts (profile, graph, summary, and report).
    """
    
    def __init__(self):
        self._memory_db: Dict[str, Dict[str, Any]] = {}
        self.storage_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "storage", "repos"
        )
        os.makedirs(self.storage_dir, exist_ok=True)
        self._load_persisted()

    def _repo_dir(self, repo_id: str) -> str:
        return os.path.join(self.storage_dir, repo_id)

    def _load_persisted(self) -> None:
        if not os.path.isdir(self.storage_dir):
            return
        for repo_id in os.listdir(self.storage_dir):
            repo_dir = self._repo_dir(repo_id)
            if not os.path.isdir(repo_dir):
                continue
            try:
                profile_path = os.path.join(repo_dir, "repository_profile.json")
                graph_path = os.path.join(repo_dir, "repository_graph.json")
                summary_path = os.path.join(repo_dir, "repository_summary.json")
                report_path = os.path.join(repo_dir, "repository_report.md")
                if not all(os.path.exists(p) for p in (profile_path, graph_path, summary_path, report_path)):
                    continue
                with open(profile_path, "r", encoding="utf-8") as f:
                    profile = json.load(f)
                with open(graph_path, "r", encoding="utf-8") as f:
                    graph = json.load(f)
                with open(summary_path, "r", encoding="utf-8") as f:
                    summary = json.load(f)
                with open(report_path, "r", encoding="utf-8") as f:
                    report = f.read()
                self._memory_db[repo_id] = {
                    "repo_id": repo_id,
                    "profile": profile,
                    "graph": graph,
                    "summary": summary,
                    "report": report,
                }
            except (json.JSONDecodeError, OSError):
                continue

    def store(
        self, 
        repo_id: str, 
        profile: Dict[str, Any], 
        graph: Dict[str, Any], 
        summary: Dict[str, Any], 
        report_markdown: str
    ) -> Dict[str, Any]:
        """
        Stores repository intelligence artifacts in memory and on disk.
        """
        intelligence_payload = {
            "repo_id": repo_id,
            "profile": profile,
            "graph": graph,
            "summary": summary,
            "report": report_markdown
        }
        self._memory_db[repo_id] = intelligence_payload
        self.export_as_json_files(repo_id, self._repo_dir(repo_id))
        return intelligence_payload

    def retrieve(self, repo_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves repository intelligence artifacts by repo ID.
        """
        return self._memory_db.get(repo_id)

    def export_as_json_files(self, repo_id: str, output_dir: str) -> Dict[str, str]:
        """
        Writes structured intelligence files to a target directory.
        """
        data = self.retrieve(repo_id)
        if not data:
            raise ValueError(f"No intelligence artifacts found for repo: {repo_id}")

        os.makedirs(output_dir, exist_ok=True)
        
        profile_path = os.path.join(output_dir, "repository_profile.json")
        graph_path = os.path.join(output_dir, "repository_graph.json")
        summary_path = os.path.join(output_dir, "repository_summary.json")
        report_path = os.path.join(output_dir, "repository_report.md")

        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(data["profile"], f, indent=2)

        with open(graph_path, "w", encoding="utf-8") as f:
            json.dump(data["graph"], f, indent=2)

        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(data["summary"], f, indent=2)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(data["report"])

        return {
            "profile": profile_path,
            "graph": graph_path,
            "summary": summary_path,
            "report": report_path
        }

# Global singleton service instance for easy access across the controllers
memory_service = RepositoryMemoryService()
