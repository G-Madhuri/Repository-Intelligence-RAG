import json
import logging
from typing import List, Dict, Any, Tuple
from memory.embedding_service import EmbeddingService
from memory.vector_store import VectorStore

logger = logging.getLogger("knowledge_index")

class KnowledgeIndexBuilder:
    def __init__(self, embedding_service: EmbeddingService, vector_store: VectorStore):
        self.embedder = embedding_service
        self.store = vector_store

    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """Simple sliding window text splitter."""
        if not text:
            return []
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunks.append(text[start:end])
            start += chunk_size - overlap
            
            # Prevent infinite loop if overlap >= chunk_size
            if chunk_size - overlap <= 0:
                break
                
        return chunks

    def build_index(
        self,
        repo_id: str,
        profile: Dict[str, Any],
        summary: Dict[str, Any],
        graph: Dict[str, Any],
        report: str,
        flat_files: List[Dict[str, Any]]
    ):
        """Builds and indexes a repository's code, structure, and profile metadata into ChromaDB."""
        logger.info(f"Starting index build for repository: {repo_id}")
        
        # Clear existing collection if any
        self.store.delete_collection(repo_id)
        
        documents: List[str] = []
        metadatas: List[Dict[str, Any]] = []
        ids: List[str] = []
        
        # Helper to generate unique IDs
        def add_chunk(content: str, metadata: Dict[str, Any], prefix: str):
            chunk_id = f"{prefix}_{len(documents)}"
            documents.append(content)
            metadatas.append(metadata)
            ids.append(chunk_id)

        # 1. Index the Repository Intelligence Report (Markdown)
        report_chunks = self.chunk_text(report, chunk_size=1000, overlap=100)
        for i, chunk in enumerate(report_chunks):
            add_chunk(
                content=chunk,
                metadata={"category": "report", "chunk_index": i},
                prefix="report"
            )

        # 2. Index the Summary details
        elevator_pitch = summary.get("elevator_pitch", "")
        if elevator_pitch:
            add_chunk(
                content=f"Project Elevator Pitch:\n{elevator_pitch}",
                metadata={"category": "summary", "subcategory": "elevator_pitch"},
                prefix="summary_pitch"
            )
            
        for feat in summary.get("core_features", []):
            add_chunk(
                content=f"Core Feature: {feat}",
                metadata={"category": "summary", "subcategory": "core_feature"},
                prefix="summary_feat"
            )
            
        for start_point in summary.get("developer_start_points", []):
            add_chunk(
                content=f"Developer Starting Point File: {start_point}",
                metadata={"category": "summary", "subcategory": "developer_start_point"},
                prefix="summary_start"
            )

        # 3. Index Profile Metadata (Architecture, APIs, Auth, Dependencies)
        arch_pattern = profile.get("architecture_pattern", "")
        if arch_pattern:
            add_chunk(
                content=f"Architecture Pattern: {arch_pattern}",
                metadata={"category": "architecture", "pattern": arch_pattern},
                prefix="profile_arch"
            )
            
        for auth_method in profile.get("authentication_methods", []):
            add_chunk(
                content=f"Authentication / Security Method: {auth_method}",
                metadata={"category": "authentication", "method": auth_method},
                prefix="profile_auth"
            )
            
        for endpoint in profile.get("api_endpoints", []):
            add_chunk(
                content=f"API Endpoint / Route: {endpoint}",
                metadata={"category": "api", "endpoint": endpoint},
                prefix="profile_api"
            )
            
        for dep in profile.get("dependencies", []):
            add_chunk(
                content=f"Package Dependency: {dep}",
                metadata={"category": "dependency", "dependency": dep},
                prefix="profile_dep"
            )

        # 4. Index Business Flows & Concepts from Graph
        for flow in graph.get("business_flows", []):
            flow_name = flow.get("flow_name", "")
            flow_desc = flow.get("description", "")
            flow_steps = ", ".join(flow.get("steps", []))
            add_chunk(
                content=f"Business Flow: {flow_name}\nDescription: {flow_desc}\nSteps: {flow_steps}",
                metadata={"category": "business_flow", "flow_name": flow_name},
                prefix="graph_flow"
            )
            
        for concept in graph.get("concepts", []):
            concept_name = concept.get("name", "")
            concept_desc = concept.get("description", "")
            concept_files = ", ".join(concept.get("files", []))
            add_chunk(
                content=f"Core Concept: {concept_name}\nDescription: {concept_desc}\nFiles: {concept_files}",
                metadata={"category": "concept", "concept_name": concept_name},
                prefix="graph_concept"
            )

        # 5. Index Source Code Files Content
        for f in flat_files:
            file_path = f.get("path", "")
            content = f.get("content", "")
            file_size = f.get("size", 0)
            
            # Skip massive files to avoid cluttering vector space
            if file_size > 100 * 1024 or not content:
                continue
                
            file_chunks = self.chunk_text(content, chunk_size=1000, overlap=100)
            for j, chunk in enumerate(file_chunks):
                # Include path info inside the document text to maintain retrieval association
                chunk_content = f"File: {file_path} (Chunk {j+1}/{len(file_chunks)})\n\n{chunk}"
                add_chunk(
                    content=chunk_content,
                    metadata={"category": "file", "path": file_path, "chunk_index": j},
                    prefix="file_chunk"
                )

        if not documents:
            logger.info("No documents found to index.")
            return

        # 6. Generate Embeddings in Batches of 50 to respect API rate limits and connection pooling
        batch_size = 50
        logger.info(f"Generating embeddings for {len(documents)} document chunks in batches of {batch_size}...")
        
        all_embeddings: List[List[float]] = []
        for start_idx in range(0, len(documents), batch_size):
            end_idx = min(start_idx + batch_size, len(documents))
            batch_docs = documents[start_idx:end_idx]
            batch_embeddings = self.embedder.embed_texts(batch_docs)
            all_embeddings.extend(batch_embeddings)
            
        # 7. Write to Vector Store
        self.store.add_documents(
            repo_id=repo_id,
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            embeddings=all_embeddings
        )
        logger.info(f"Vector database indexing complete. Indexed {len(documents)} chunks.")
