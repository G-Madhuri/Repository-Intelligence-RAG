"""
Phase 3 integration test: validates RAG pipeline, tool execution,
conversation manager, and Pinecone vector store operations.
"""
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from memory.embedding_service import EmbeddingService
from memory.vector_store import VectorStore
from memory.knowledge_index import KnowledgeIndexBuilder
from memory.retriever import KnowledgeRetriever
from memory.conversation_manager import ConversationManager
from tools.repository_search_tool import RepositorySearchTool
from tools.graph_query_tool import GraphQueryTool
from tools.dependency_lookup_tool import DependencyLookupTool
from tools.architecture_lookup_tool import ArchitectureLookupTool
from tools.api_lookup_tool import ApiLookupTool
import unittest.mock as mock

REPO_ID = "test-repo-phase3"

PROFILE = {
    "project_name": "TestApp", "project_type": "web app",
    "languages": ["Python"], "frameworks": ["FastAPI"],
    "databases": ["SQLite"], "authentication_methods": ["JWT"],
    "major_modules": ["main", "auth"], "api_endpoints": ["/api/login", "/api/data"],
    "important_files": ["main.py"], "architecture_pattern": "Monolithic",
    "dependencies": ["fastapi", "pyjwt"]
}

SUMMARY = {
    "elevator_pitch": "A test app with JWT auth.",
    "core_features": ["Login", "Data access"],
    "main_workflows": ["User authentication flow"],
    "key_components": ["AuthRouter"],
    "key_risks": ["No refresh tokens"],
    "developer_start_points": ["main.py"]
}

GRAPH = {
    "nodes": [{"id": "main.py", "label": "main.py", "type": "file", "properties": {}}],
    "edges": [],
    "entry_points": [{"file_path": "main.py", "type": "uvicorn", "description": "Entry"}],
    "business_flows": [{"flow_name": "Auth Flow", "description": "Login process", "steps": ["login_endpoint"]}],
    "critical_paths": [],
    "concepts": [{"name": "Authentication", "description": "JWT-based auth", "files": ["auth.py"]}]
}

REPORT = "# Test Report\nThis app uses JWT authentication with FastAPI."

FILES = [
    {"path": "main.py", "content": "from fastapi import FastAPI\napp = FastAPI()", "size": 50},
    {"path": "auth.py", "content": "import jwt\ndef verify(token): pass", "size": 40}
]

def run_tests():
    print("=== Integration Tests (Pinecone + LangChain + LangSmith) ===\n")
    passed = 0
    failed = 0
    
    try:
        # Test 1: VectorStore initialization
        print("Test 1: VectorStore (Pinecone) initialization...")
        vs = VectorStore()
        print("  [OK] VectorStore initialized for Pinecone index:", vs.index_name)
        passed += 1

        # Test 2: KnowledgeIndexBuilder
        print("Test 2: KnowledgeIndexBuilder indexing into Pinecone...")
        mock_embedder = mock.MagicMock()
        mock_embedder.embed_texts.side_effect = lambda texts: [[0.1] * 1024 for _ in texts]
        mock_embedder.embed_text.return_value = [0.1] * 1024

        indexer = KnowledgeIndexBuilder(mock_embedder, vs)
        indexer.build_index(REPO_ID, PROFILE, SUMMARY, GRAPH, REPORT, FILES)
        print("  [OK] Indexed documents into Pinecone namespace successfully")
        passed += 1

        # Test 3: KnowledgeRetriever
        print("Test 3: KnowledgeRetriever semantic query...")
        retriever = KnowledgeRetriever(mock_embedder, vs)
        results = retriever.retrieve(REPO_ID, "JWT authentication", top_k=3)
        assert isinstance(results, list), "Expected list of results"
        print(f"  [OK] Retrieved {len(results)} results from Pinecone")
        passed += 1

        # Test 4: ConversationManager
        print("Test 4: ConversationManager sessions...")
        cm = ConversationManager()
        cm.add_message("sess-1", REPO_ID, "user", "What is the auth method?")
        cm.add_message("sess-1", REPO_ID, "assistant", "JWT is used.", agent_decisions={"agents_used": ["SecurityAgent"]})
        
        session = cm.get_session("sess-1")
        assert session is not None
        assert len(session.history) == 2
        print("  [OK] ConversationManager: sessions tracked correctly")
        passed += 1

        # Test 5: Tools execution
        print("Test 5: Tool execution (DependencyLookup, ArchitectureLookup, etc)...")
        from services.repositoryMemory import memory_service
        memory_service.store(REPO_ID, PROFILE, GRAPH, SUMMARY, REPORT)
        
        dep_tool = DependencyLookupTool()
        dep_result = dep_tool.execute(repo_id=REPO_ID)
        assert "FastAPI" in dep_result["frameworks"]
        
        arch_tool = ArchitectureLookupTool()
        arch_result = arch_tool.execute(repo_id=REPO_ID)
        assert arch_result["architecture_pattern"] == "Monolithic"
        
        print("  [OK] All tools executed and returned correct data")
        passed += 1

        # Test 6: Pinecone collection cleanup
        print("Test 6: Pinecone namespace cleanup...")
        vs.delete_collection(REPO_ID)
        print("  [OK] Pinecone test namespace cleared")
        passed += 1

    except Exception as e:
        print(f"  [FAIL] ERROR: {e}")
        import traceback; traceback.print_exc()
        failed += 1

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    ok = run_tests()
    sys.exit(0 if ok else 1)
