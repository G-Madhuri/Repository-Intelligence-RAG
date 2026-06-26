from tools.base_tool import BaseTool
from memory.vector_store import VectorStore
from typing import Any
import logging

logger = logging.getLogger("file_reader_tool")

class FileReaderTool(BaseTool):
    def __init__(self, vector_store: VectorStore):
        self.store = vector_store

    @property
    def name(self) -> str:
        return "file_reader"

    @property
    def description(self) -> str:
        return "Reads the content of a specific source code file by retrieving its chunks. Inputs: repo_id (str), path (str)."

    def execute(self, **kwargs) -> Any:
        repo_id = kwargs.get("repo_id")
        path = kwargs.get("path")
        if not repo_id or not path:
            return {"error": "Missing required parameters: repo_id and path."}
            
        try:
            collection = self.store.get_collection(repo_id)
            results = collection.get(where={"path": path})
            
            if not results or not results.get("documents"):
                return {"error": f"File '{path}' not found in knowledge index."}
                
            docs = results["documents"]
            metas = results["metadatas"]
            
            # Reconstruct sorting by chunk index
            chunks = []
            for doc, meta in zip(docs, metas):
                idx = meta.get("chunk_index", 0)
                chunks.append((idx, doc))
            chunks.sort(key=lambda x: x[0])
            
            # Rebuild file and remove the file header prefix
            content_builder = []
            for idx, content in chunks:
                if "\n\n" in content and content.startswith("File: "):
                    parts = content.split("\n\n", 1)
                    content_builder.append(parts[1])
                else:
                    content_builder.append(content)
                    
            return {
                "path": path,
                "content": "".join(content_builder),
                "chunks_found": len(chunks)
            }
        except Exception as e:
            logger.error(f"Error executing file_reader tool: {e}")
            return {"error": f"Failed to retrieve file contents: {str(e)}"}
