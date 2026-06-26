import os
import json
import shutil
import tempfile
import uuid
import logging
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask
from pydantic import BaseModel

# Load .env variables manually if the file is present
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

# Import services
from services.repositoryScanner import (
    check_repository_privacy, 
    clone_repository, 
    extract_zip, 
    scan_directory,
    handle_remove_readonly
)
from services.repositoryProfiler import profile_repository
from services.graphBuilder import build_initial_graph
from services.llmAnalyzer import analyze_repository
from services.repositoryMemory import memory_service

# Phase 3: Memory, RAG, Tools
from memory.embedding_service import EmbeddingService
from memory.vector_store import VectorStore
from memory.knowledge_index import KnowledgeIndexBuilder
from memory.retriever import KnowledgeRetriever
from memory.conversation_manager import conversation_manager
from memory.session_manager import session_manager
from memory.memory_cache import memory_cache
# Singleton memory infrastructure (initialised lazily per-request)
_vector_store: VectorStore = None

def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI(
    title="Repository Intelligence API",
    description="Foundational Memory and Intelligence Layer for Multi-Agent AI Software Engineering",
    version="1.0.0"
)

# Enable CORS for frontend integration (credentials disabled when using wildcard origins)
_cors_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials="*" not in _cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request schema for analyzing git repository
class AnalyzeUrlRequest(BaseModel):
    url: str
    token: Optional[str] = None

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}

@app.post("/api/analyze-url")
async def analyze_git_url(
    request: AnalyzeUrlRequest,
    x_gemini_key: Optional[str] = Header(None)
):
    """
    Clones a GitHub repository, validates access permissions, processes the pipeline,
    calls Gemini 2.5 Flash, and returns structured intelligence outputs.
    """
    repo_url = request.url
    token = request.token
    gemini_key = x_gemini_key or os.environ.get("GEMINI_API_KEY")

    if not gemini_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gemini API Key is missing. Please provide it in the headers (x-gemini-key) or configure it on the server."
        )

    # 1. Validate repository privacy and access
    logger.info(f"Validating access to repository: {repo_url}")
    privacy_info = await check_repository_privacy(repo_url, token)
    
    if privacy_info["status"] in ["private_requires_auth", "private_denied"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=privacy_info["message"]
        )
    elif privacy_info["status"] == "invalid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=privacy_info["message"]
        )
    elif privacy_info["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=privacy_info["message"]
        )

    owner_repo = privacy_info["owner_repo"] or "cloned_repo"
    repo_id = str(uuid.uuid4())

    # Create a temporary directory in a secure, OS-agnostic manner
    temp_dir = tempfile.mkdtemp(prefix="repo_intel_")
    
    try:
        # 2. Clone the repository
        logger.info(f"Cloning repository into temporary directory: {temp_dir}")
        clone_repository(repo_url, temp_dir, token)
        
        # 3. Scan the repository file tree and text files
        logger.info("Scanning directory structure...")
        scan_results = scan_directory(temp_dir)
        
        # 4. Generate static profile and basic relationship graph
        logger.info("Generating static profiles...")
        static_profile = profile_repository(scan_results["files"])
        static_graph = build_initial_graph(scan_results["files"])
        static_profile["static_graph"] = static_graph
        
        # 5. Call LLM for deep reasoning and structured outputs
        logger.info("Triggering Gemini 2.5 Flash intelligence analysis...")
        analysis_result = await analyze_repository(
            repo_name=owner_repo,
            tree_structure=scan_results["tree"],
            static_profile=static_profile,
            flat_files=scan_results["files"],
            api_key=gemini_key
        )
        
        # 6. Save outputs inside the repositoryMemory service
        logger.info("Storing generated artifacts in memory layer...")
        stored = memory_service.store(
            repo_id=repo_id,
            profile=analysis_result["profile"],
            graph=analysis_result["graph"],
            summary=analysis_result["summary"],
            report_markdown=analysis_result["report"]
        )

        # 7. Phase 3: Build semantic vector index asynchronously
        gemini_key_for_embed = gemini_key
        try:
            logger.info("Building semantic knowledge index (ChromaDB)...")
            import asyncio
            embedder = EmbeddingService(api_key=gemini_key_for_embed)
            vs = get_vector_store()
            indexer = KnowledgeIndexBuilder(embedder, vs)
            await asyncio.to_thread(
                indexer.build_index,
                repo_id,
                analysis_result["profile"],
                analysis_result["summary"],
                analysis_result["graph"],
                analysis_result["report"],
                scan_results["files"]
            )
            logger.info(f"Knowledge index built for repo {repo_id}.")
        except Exception as idx_e:
            logger.warning(f"Knowledge index build failed (non-fatal): {idx_e}")
        
        return {
            "success": True,
            "repo_id": repo_id,
            "project_name": owner_repo,
            "tree": scan_results["tree"],
            "data": stored
        }

    except Exception as e:
        logger.error(f"Error during repository analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )
    finally:
        # Clean up temporary directory (safe rmtree for Windows/Linux read-only files)
        logger.info(f"Cleaning up temporary workspace directory: {temp_dir}")
        shutil.rmtree(temp_dir, onerror=handle_remove_readonly)

@app.post("/api/analyze-zip")
async def analyze_uploaded_zip(
    file: UploadFile = File(...),
    x_gemini_key: Optional[str] = Header(None)
):
    """
    Extracts an uploaded repository ZIP file, runs structural scanning,
    generates static/dynamic profile schemas, and runs the LLM analysis.
    """
    gemini_key = x_gemini_key or os.environ.get("GEMINI_API_KEY")

    if not gemini_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gemini API Key is missing. Please provide it in the headers (x-gemini-key) or configure it on the server."
        )

    if not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only ZIP archives are supported."
        )

    repo_id = str(uuid.uuid4())
    project_name = file.filename[:-4]  # Strip .zip

    # Set up temporary directory and paths
    temp_dir = tempfile.mkdtemp(prefix="zip_intel_")
    fd, zip_path = tempfile.mkstemp(suffix=".zip")
    
    try:
        # Save ZIP upload chunk by chunk
        with os.fdopen(fd, 'wb') as tmp_zip:
            shutil.copyfileobj(file.file, tmp_zip)

        # 1. Extract ZIP securely with path traversal protection
        logger.info(f"Extracting zip archive: {file.filename}")
        extract_zip(zip_path, temp_dir)
        
        # 2. Scan directory
        logger.info("Scanning unzipped directory structure...")
        scan_results = scan_directory(temp_dir)
        
        # 3. Generate static profiles
        logger.info("Generating static profiles...")
        static_profile = profile_repository(scan_results["files"])
        static_graph = build_initial_graph(scan_results["files"])
        static_profile["static_graph"] = static_graph
        
        # 4. Trigger Gemini analysis
        logger.info("Analyzing unzipped codebase with Gemini 2.5 Flash...")
        analysis_result = await analyze_repository(
            repo_name=project_name,
            tree_structure=scan_results["tree"],
            static_profile=static_profile,
            flat_files=scan_results["files"],
            api_key=gemini_key
        )
        
        # 5. Store generated artifacts
        logger.info("Storing artifacts in memory service...")
        stored = memory_service.store(
            repo_id=repo_id,
            profile=analysis_result["profile"],
            graph=analysis_result["graph"],
            summary=analysis_result["summary"],
            report_markdown=analysis_result["report"]
        )

        # 6. Phase 3: Build semantic vector index
        try:
            logger.info("Building semantic knowledge index for ZIP repo...")
            import asyncio
            embedder = EmbeddingService(api_key=gemini_key)
            vs = get_vector_store()
            indexer = KnowledgeIndexBuilder(embedder, vs)
            await asyncio.to_thread(
                indexer.build_index,
                repo_id,
                analysis_result["profile"],
                analysis_result["summary"],
                analysis_result["graph"],
                analysis_result["report"],
                scan_results["files"]
            )
            logger.info(f"Knowledge index built for ZIP repo {repo_id}.")
        except Exception as idx_e:
            logger.warning(f"Knowledge index build failed (non-fatal): {idx_e}")
        
        return {
            "success": True,
            "repo_id": repo_id,
            "project_name": project_name,
            "tree": scan_results["tree"],
            "data": stored
        }

    except Exception as e:
        logger.error(f"Error processing uploaded zip file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )
    finally:
        # Cleanup
        logger.info(f"Cleaning up temporary workspace files...")
        if os.path.exists(zip_path):
            os.remove(zip_path)
        shutil.rmtree(temp_dir, onerror=handle_remove_readonly)

def _cleanup_temp_dir(path: str) -> None:
    if os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)


@app.get("/api/download/{repo_id}/{artifact_type}")
async def download_intelligence_artifact(repo_id: str, artifact_type: str):
    """
    Downloads specific intelligence output as files (profile.json, graph.json, summary.json, report.md)
    """
    data = memory_service.retrieve(repo_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository intelligence data not found or has expired."
        )

    artifact_map = {
        "profile": ("repository_profile.json", "application/json", lambda d: json.dumps(d["profile"], indent=2)),
        "graph": ("repository_graph.json", "application/json", lambda d: json.dumps(d["graph"], indent=2)),
        "summary": ("repository_summary.json", "application/json", lambda d: json.dumps(d["summary"], indent=2)),
        "report": ("repository_report.md", "text/markdown", lambda d: d["report"]),
    }

    if artifact_type not in artifact_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid artifact type: {artifact_type}"
        )

    filename, media_type, content_fn = artifact_map[artifact_type]
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, filename)

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content_fn(data))
        return FileResponse(
            file_path,
            media_type=media_type,
            filename=filename,
            background=BackgroundTask(_cleanup_temp_dir, temp_dir),
        )
    except Exception as e:
        _cleanup_temp_dir(temp_dir)
        logger.error(f"Error compiling download file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download file."
        )

class ChatRequest(BaseModel):
    repo_id: str
    question: str
    session_id: Optional[str] = None

@app.post("/api/chat")
async def chat_with_repo(
    request: ChatRequest,
    x_gemini_key: Optional[str] = Header(None)
):
    """
    Phase 2+3: Executes the multi-agent orchestration pipeline with RAG context
    retrieval and conversation memory.
    """
    import time
    import asyncio
    from agents.llm_client import GeminiLLMClient
    from agents.orchestrator import AgentOrchestrator

    gemini_key = x_gemini_key or os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gemini API Key is missing."
        )

    repo_data = memory_service.retrieve(request.repo_id)
    if not repo_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository intelligence data not found or has expired."
        )

    session_id = request.session_id or str(uuid.uuid4())

    # Add user message to memory first
    conversation_manager.add_message(
        session_id=session_id,
        repo_id=request.repo_id,
        role="user",
        content=request.question
    )

    try:
        llm_client = GeminiLLMClient(api_key=gemini_key)
        orchestrator = AgentOrchestrator(llm_client)
        
        embedder = EmbeddingService(api_key=gemini_key)
        retriever = KnowledgeRetriever(embedder, get_vector_store())

        logger.info(f"Orchestrating agents for repo {request.repo_id}: '{request.question}'")

        # Run pipeline
        result = await orchestrator.execute(
            profile=repo_data["profile"],
            graph=repo_data["graph"],
            summary=repo_data["summary"],
            report=repo_data["report"],
            query=request.question,
            repo_id=request.repo_id,
            session_id=session_id,
            vector_store=get_vector_store(),
            retriever=retriever
        )

        # Attach session and RAG details
        result["session_id"] = session_id
        
        # Populate retrieved context on user message
        session = conversation_manager.get_session(session_id)
        if session and session.history:
            session.history[-1].retrieved_context = result.get("retrieved_context", [])

        # Store assistant response in conversation memory
        conversation_manager.add_message(
            session_id=session_id,
            repo_id=request.repo_id,
            role="assistant",
            content=result.get("answer", ""),
            agent_decisions={
                "agents_used": result.get("agents_used", []),
                "confidence": result.get("confidence", 0.0),
                "planner_decision": result.get("planner_decision", {})
            }
        )

        # Persist conversation sessions to disk
        session_manager.save_all()

        return result

    except Exception as e:
        logger.error(f"Chat orchestration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat execution failed: {str(e)}"
        )


class SearchRequest(BaseModel):
    repo_id: str
    query: str
    top_k: int = 5
    category: Optional[str] = None

@app.post("/api/search")
async def semantic_search(
    request: SearchRequest,
    x_gemini_key: Optional[str] = Header(None)
):
    """Phase 3: Semantic search against the repository knowledge vector index."""
    import time
    gemini_key = x_gemini_key or os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        raise HTTPException(status_code=400, detail="Gemini API Key required for semantic search.")

    repo_data = memory_service.retrieve(request.repo_id)
    if not repo_data:
        raise HTTPException(status_code=404, detail="Repository data not found.")

    try:
        start = time.time()
        embedder = EmbeddingService(api_key=gemini_key)
        retriever = KnowledgeRetriever(embedder, get_vector_store())
        results = retriever.retrieve(
            repo_id=request.repo_id,
            query=request.query,
            top_k=request.top_k,
            category=request.category
        )
        latency_ms = int((time.time() - start) * 1000)
        return {
            "query": request.query,
            "results": results,
            "result_count": len(results),
            "latency_ms": latency_ms
        }
    except Exception as e:
        logger.error(f"Semantic search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/api/memory")
async def get_memory_info(repo_id: str):
    """Phase 3: Returns vector index stats for a repository."""
    try:
        vs = get_vector_store()
        count = vs.count_documents(repo_id)
        return {
            "repo_id": repo_id,
            "indexed_chunks": count,
            "storage_path": vs.storage_path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations")
async def list_conversations(repo_id: str):
    """Phase 3: Returns conversation sessions for a repository."""
    sessions = conversation_manager.list_sessions_for_repo(repo_id)
    return {"repo_id": repo_id, "sessions": sessions}


@app.get("/api/conversations/{session_id}")
async def get_conversation(session_id: str):
    """Returns full message history for a conversation session."""
    history = session_manager.get_session_history(session_id)
    if history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation session not found."
        )
    return {"session_id": session_id, "history": history}


@app.get("/api/tools")
async def list_tools():
    """Phase 3: Returns the registered tool catalog (MCP-ready)."""
    tools = [
        {"name": "repository_search",    "description": "Semantic search over indexed repo chunks."},
        {"name": "graph_query",           "description": "Query architecture graph, entry points, and flows."},
        {"name": "dependency_lookup",     "description": "Lookup packages, frameworks, and databases."},
        {"name": "file_reader",           "description": "Retrieve specific source file content."},
        {"name": "architecture_lookup",   "description": "Query architecture pattern and key modules."},
        {"name": "api_lookup",            "description": "Lookup HTTP routes and authentication methods."}
    ]
    return {"tools": tools, "count": len(tools)}

# Serve static frontend build if present
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
if os.path.exists(frontend_dist):
    logger.info(f"Serving static frontend files from: {frontend_dist}")
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")
else:
    logger.warning(f"Frontend dist folder not found at {frontend_dist}. Running in API-only mode.")

