"""
Phase 3 integration test: validates RAG pipeline, tool execution,
conversation manager, and vector store operations without hitting live APIs.
"""
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(__file__))

# â”€â”€ Mock EmbeddingService â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
import tempfile, shutil

# â”€â”€ Fixtures â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
    print("=== Phase 3 Integration Tests ===\n")
    tmp_dir = tempfile.mkdtemp(prefix="phase3_test_")
    passed = 0
    failed = 0
    
    try:
        # â”€â”€ Test 1: VectorStore create / count â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        print("Test 1: VectorStore initialization...")
        vs = VectorStore(storage_path=tmp_dir)
        count = vs.count_documents(REPO_ID)
        assert count == 0, f"Expected 0, got {count}"
        print("  âœ“ VectorStore initialized, empty collection count = 0")
        passed += 1

        # â”€â”€ Test 2: KnowledgeIndexBuilder with mocked embedder â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        print("Test 2: KnowledgeIndexBuilder with mocked embeddings...")
        mock_embedder = mock.MagicMock()
        # Return exactly N vectors where N = len of input texts
        mock_embedder.embed_texts.side_effect = lambda texts: [[0.1] * 768 for _ in texts]
        mock_embedder.embed_text.return_value = [0.1] * 768

        indexer = KnowledgeIndexBuilder(mock_embedder, vs)
        indexer.build_index(REPO_ID, PROFILE, SUMMARY, GRAPH, REPORT, FILES)
        
        count_after = vs.count_documents(REPO_ID)
        assert count_after > 0, f"Expected chunks indexed, got {count_after}"
        print(f"  âœ“ Indexed {count_after} chunks successfully")
        passed += 1

        # â”€â”€ Test 3: KnowledgeRetriever â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        print("Test 3: KnowledgeRetriever semantic query...")
        retriever = KnowledgeRetriever(mock_embedder, vs)
        results = retriever.retrieve(REPO_ID, "JWT authentication", top_k=3)
        assert isinstance(results, list), "Expected list of results"
        assert len(results) <= 3, f"Expected at most 3, got {len(results)}"
        if results:
            assert "content" in results[0]
            assert "similarity" in results[0]
        print(f"  âœ“ Retrieved {len(results)} results with similarity scores")
        passed += 1

        # â”€â”€ Test 4: Category-filtered retrieval â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        print("Test 4: Filtered retrieval by category 'authentication'...")
        auth_results = retriever.retrieve(REPO_ID, "login security", top_k=5, category="authentication")
        assert isinstance(auth_results, list)
        print(f"  âœ“ Filtered retrieval returned {len(auth_results)} authentication chunks")
        passed += 1

        # â”€â”€ Test 5: ConversationManager â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        print("Test 5: ConversationManager sessions...")
        cm = ConversationManager()
        cm.add_message("sess-1", REPO_ID, "user", "What is the auth method?")
        cm.add_message("sess-1", REPO_ID, "assistant", "JWT is used.", agent_decisions={"agents_used": ["SecurityAgent"]})
        cm.add_message("sess-2", REPO_ID, "user", "List all endpoints.")
        
        session = cm.get_session("sess-1")
        assert session is not None
        assert len(session.history) == 2
        assert session.history[0].role == "user"
        assert session.history[1].agent_decisions["agents_used"] == ["SecurityAgent"]
        
        sessions_for_repo = cm.list_sessions_for_repo(REPO_ID)
        assert len(sessions_for_repo) == 2
        print(f"  âœ“ ConversationManager: {len(sessions_for_repo)} sessions, history tracked")
        passed += 1

        # â”€â”€ Test 6: Tools execute â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        print("Test 6: Tool execution (DependencyLookup, ArchitectureLookup)...")
        from services.repositoryMemory import memory_service
        memory_service.store(REPO_ID, PROFILE, GRAPH, SUMMARY, REPORT)
        
        dep_tool = DependencyLookupTool()
        dep_result = dep_tool.execute(repo_id=REPO_ID)
        assert "frameworks" in dep_result
        assert "FastAPI" in dep_result["frameworks"]
        
        arch_tool = ArchitectureLookupTool()
        arch_result = arch_tool.execute(repo_id=REPO_ID)
        assert arch_result["architecture_pattern"] == "Monolithic"
        
        api_tool = ApiLookupTool()
        api_result = api_tool.execute(repo_id=REPO_ID)
        assert "/api/login" in api_result["api_endpoints"]
        
        graph_tool = GraphQueryTool()
        graph_result = graph_tool.execute(repo_id=REPO_ID)
        assert "business_flows" in graph_result
        
        search_tool = RepositorySearchTool(retriever)
        search_result = search_tool.execute(repo_id=REPO_ID, query="authentication")
        assert "results" in search_result
        
        print("  âœ“ All 5 tools executed and returned correct data")
        passed += 1

        # â”€â”€ Test 7: VectorStore delete â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        print("Test 7: VectorStore collection deletion...")
        vs.delete_collection(REPO_ID)
        count_deleted = vs.count_documents(REPO_ID)
        assert count_deleted == 0
        print("  âœ“ Collection deleted, count = 0")
        passed += 1

    except AssertionError as e:
        print(f"  âœ— ASSERTION FAILED: {e}")
        failed += 1
    except Exception as e:
        print(f"  âœ— UNEXPECTED ERROR: {e}")
        import traceback; traceback.print_exc()
        failed += 1
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")
    if failed == 0:
        print("All Phase 3 integration tests passed! âœ“")
    else:
        print("Some tests FAILED.")
    return failed == 0

if __name__ == "__main__":
    ok = run_tests()
    sys.exit(0 if ok else 1)

