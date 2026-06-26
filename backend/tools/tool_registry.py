from typing import Dict, Any, List
from tools.base_tool import BaseTool
from tools.repository_search_tool import RepositorySearchTool
from tools.graph_query_tool import GraphQueryTool
from tools.dependency_lookup_tool import DependencyLookupTool
from tools.file_reader_tool import FileReaderTool
from tools.architecture_lookup_tool import ArchitectureLookupTool
from tools.api_lookup_tool import ApiLookupTool

class ToolRegistry:
    """
    Registry for managing and executing repository intelligence tools.
    Compatible with agent planners and the Model Context Protocol (MCP).
    """
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> BaseTool:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, str]]:
        return [
            {"name": tool.name, "description": tool.description}
            for tool in self._tools.values()
        ]

    def execute_tool(self, name: str, **kwargs) -> Any:
        tool = self.get_tool(name)
        if not tool:
            return {"error": f"Tool '{name}' not found in registry."}
        try:
            return tool.execute(**kwargs)
        except Exception as e:
            return {"error": f"Error executing tool '{name}': {str(e)}"}

# Global tool registry instance
tool_registry = ToolRegistry()

def setup_default_registry(vector_store, retriever):
    """Utility to register all standard repository tools with dependencies."""
    tool_registry.register(RepositorySearchTool(retriever))
    tool_registry.register(FileReaderTool(vector_store))
    tool_registry.register(GraphQueryTool())
    tool_registry.register(DependencyLookupTool())
    tool_registry.register(ArchitectureLookupTool())
    tool_registry.register(ApiLookupTool())
