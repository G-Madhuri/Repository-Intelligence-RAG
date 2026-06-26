from tools.base_tool import BaseTool
from memory.retriever import KnowledgeRetriever
from typing import Any

class RepositorySearchTool(BaseTool):
    def __init__(self, retriever: KnowledgeRetriever):
        self.retriever = retriever

    @property
    def name(self) -> str:
        return "repository_search"

    @property
    def description(self) -> str:
        return "Searches the codebase semantically for matching text, logic, or functions. Inputs: repo_id (str), query (str), top_k (int, optional)."

    def execute(self, **kwargs) -> Any:
        repo_id = kwargs.get("repo_id")
        query = kwargs.get("query")
        top_k = kwargs.get("top_k", 5)
        
        if not repo_id or not query:
            return {"error": "Missing required parameters: repo_id and query."}
            
        results = self.retriever.retrieve(repo_id=repo_id, query=query, top_k=top_k)
        return {
            "results": [
                {
                    "content": r["content"],
                    "metadata": r["metadata"],
                    "similarity": r["similarity"]
                }
                for r in results
            ]
        }
