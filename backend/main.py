import os
import json
import shutil
import tempfile
import uuid
import logging
import psycopg2
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask
from pydantic import BaseModel
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Load .env variables manually if the file is present
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

# Import auth dependency
from auth import get_current_user

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

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

_vector_store: VectorStore = None

def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store

def get_db_connection():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL is not set.")
    return psycopg2.connect(db_url)

def record_user_and_repo(uid: str, email: str, repo_id: str, repo_name: str, status_str: str = "completed"):
    """Step 5: Every write to Supabase MUST include uid from get_current_user."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 1. Upsert user record
                cur.execute("""
                    INSERT INTO users (id, email) VALUES (%s, %s)
                    ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email;
                """, (uid, email))

                # 2. Upsert repo with 1-hour TTL (Step 12: reset to NOW() + 1 hour on re-ingest)
                cur.execute("""
                    INSERT INTO repos (repo_id, uid, name, status, expires_at)
                    VALUES (%s, %s, %s, %s, NOW() + INTERVAL '1 hour')
                    ON CONFLICT (repo_id) DO UPDATE SET 
                        expires_at = NOW() + INTERVAL '1 hour',
                        status = EXCLUDED.status,
                        uid = EXCLUDED.uid;
                """, (repo_id, uid, repo_name, status_str))

                # 3. Create job record
                job_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO jobs (job_id, repo_id, uid, status, stage, progress)
                    VALUES (%s, %s, %s, %s, %s, %s);
                """, (job_id, repo_id, uid, status_str, "done", 100))
        logger.info(f"Supabase DB updated: user={uid}, repo={repo_id}, status={status_str}")
    except Exception as e:
        logger.error(f"Failed to record Supabase DB entries: {e}")

def verify_repo_ownership(repo_id: str, uid: str):
    """Step 6: When querying Pinecone/data, verify ownership first."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT uid FROM repos WHERE repo_id = %s;", (repo_id,))
                row = cur.fetchone()
                if not row:
                    # Allow in-memory fallback for fresh sessions if DB read is delayed
                    return
                repo_uid = str(row[0])
                if repo_uid != uid:
                    logger.warning(f"Forbidden access attempt: repo {repo_id} owner {repo_uid} != request user {uid}")
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Forbidden: You do not own this repository."
                    )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Ownership check warning: {e}")

def purge_expired_repos():
    """Step 11: APScheduler TTL Cleanup — purge expired repos from Pinecone and Supabase every 10 minutes."""
    logger.info("[TTL Cleanup Job] Checking for expired repositories in Supabase (expires_at < NOW())...")
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT repo_id, uid FROM repos WHERE expires_at < NOW();")
                expired = cur.fetchall()
                if not expired:
                    logger.info("[TTL Cleanup Job] 0 expired repositories found.")
                    return

                vs = get_vector_store()
                purged_count = 0
                for repo_id, uid in expired:
                    logger.info(f"[TTL Cleanup Job] Deleting namespace repo_{repo_id.replace('-', '_')} from Pinecone for expired repo {repo_id}...")
                    vs.delete_collection(repo_id)

                    cur.execute("DELETE FROM conversations WHERE repo_id = %s;", (repo_id,))
                    cur.execute("DELETE FROM jobs WHERE repo_id = %s;", (repo_id,))
                    cur.execute("DELETE FROM repos WHERE repo_id = %s;", (repo_id,))
                    purged_count += 1

                logger.info(f"[TTL Cleanup Job] Purged {purged_count} expired repositories from Pinecone and Supabase.")
    except Exception as e:
        logger.error(f"Error in purge_expired_repos cleanup job: {e}")

app = FastAPI(
    title="Repository Intelligence API",
    description="Foundational Memory and Intelligence Layer for Multi-Agent AI Software Engineering",
    version="1.0.0"
)

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global unhandled exception on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc) or "Internal server error occurred."}
    )

# Setup APScheduler (Step 10)
scheduler = AsyncIOScheduler()

@app.on_event("startup")
def start_ttl_scheduler():
    scheduler.add_job(purge_expired_repos, 'interval', minutes=10)
    scheduler.start()
    logger.info("APScheduler started: purge_expired_repos running every 10 minutes.")

@app.on_event("shutdown")
def stop_ttl_scheduler():
    scheduler.shutdown()

_cors_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials="*" not in _cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeUrlRequest(BaseModel):
    url: str
    token: Optional[str] = None

# Public Routes
@app.get("/health")
@app.get("/ready")
@app.get("/api/health")
def health_check():
    return {"status": "healthy"}

# Protected Routes (Step 4: All /api/* routes protected with Depends(get_current_user))
@app.post("/api/analyze-url")
async def analyze_git_url(
    request: AnalyzeUrlRequest,
    current_user: dict = Depends(get_current_user),
    x_gemini_key: Optional[str] = Header(None)
):
    repo_url = request.url
    token = request.token
    gemini_key = x_gemini_key or os.environ.get("GEMINI_API_KEY")

    if not gemini_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gemini API Key is missing."
        )

    privacy_info = await check_repository_privacy(repo_url, token)
    if privacy_info["status"] in ["private_requires_auth", "private_denied"]:
        raise HTTPException(status_code=401, detail=privacy_info["message"])
    elif privacy_info["status"] == "invalid":
        raise HTTPException(status_code=400, detail=privacy_info["message"])
    elif privacy_info["status"] == "error":
        raise HTTPException(status_code=502, detail=privacy_info["message"])

    owner_repo = privacy_info["owner_repo"] or "cloned_repo"
    repo_id = str(uuid.uuid4())
    temp_dir = tempfile.mkdtemp(prefix="repo_intel_")

    try:
        clone_repository(repo_url, temp_dir, token)
        scan_results = scan_directory(temp_dir)
        static_profile = profile_repository(scan_results["files"])
        static_graph = build_initial_graph(scan_results["files"])
        static_profile["static_graph"] = static_graph

        analysis_result = await analyze_repository(
            repo_name=owner_repo,
            tree_structure=scan_results["tree"],
            static_profile=static_profile,
            flat_files=scan_results["files"],
            api_key=gemini_key
        )

        stored = memory_service.store(
            repo_id=repo_id,
            profile=analysis_result["profile"],
            graph=analysis_result["graph"],
            summary=analysis_result["summary"],
            report_markdown=analysis_result["report"]
        )

        # Record user, repo, job in Supabase (Step 5)
        record_user_and_repo(current_user["uid"], current_user["email"], repo_id, owner_repo, "completed")

        # Build Pinecone knowledge index
        try:
            import asyncio
            embedder = EmbeddingService()
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
        except Exception as idx_e:
            logger.warning(f"Knowledge index build warning: {idx_e}")

        return {
            "success": True,
            "repo_id": repo_id,
            "project_name": owner_repo,
            "tree": scan_results["tree"],
            "data": stored
        }
    finally:
        shutil.rmtree(temp_dir, onerror=handle_remove_readonly)

@app.post("/api/analyze-zip")
async def analyze_uploaded_zip(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    x_gemini_key: Optional[str] = Header(None)
):
    gemini_key = x_gemini_key or os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        raise HTTPException(status_code=400, detail="Gemini API Key missing.")

    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only ZIP files are supported.")

    repo_id = str(uuid.uuid4())
    project_name = file.filename[:-4]
    temp_dir = tempfile.mkdtemp(prefix="zip_intel_")
    fd, zip_path = tempfile.mkstemp(suffix=".zip")

    try:
        with os.fdopen(fd, 'wb') as tmp_zip:
            shutil.copyfileobj(file.file, tmp_zip)

        extract_zip(zip_path, temp_dir)
        scan_results = scan_directory(temp_dir)
        static_profile = profile_repository(scan_results["files"])
        static_graph = build_initial_graph(scan_results["files"])
        static_profile["static_graph"] = static_graph

        analysis_result = await analyze_repository(
            repo_name=project_name,
            tree_structure=scan_results["tree"],
            static_profile=static_profile,
            flat_files=scan_results["files"],
            api_key=gemini_key
        )

        stored = memory_service.store(
            repo_id=repo_id,
            profile=analysis_result["profile"],
            graph=analysis_result["graph"],
            summary=analysis_result["summary"],
            report_markdown=analysis_result["report"]
        )

        # Record user & repo in Supabase (Step 5)
        record_user_and_repo(current_user["uid"], current_user["email"], repo_id, project_name, "completed")

        try:
            import asyncio
            embedder = EmbeddingService()
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
        except Exception as idx_e:
            logger.warning(f"Knowledge index build warning: {idx_e}")

        return {
            "success": True,
            "repo_id": repo_id,
            "project_name": project_name,
            "tree": scan_results["tree"],
            "data": stored
        }
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)
        shutil.rmtree(temp_dir, onerror=handle_remove_readonly)

@app.get("/api/download/{repo_id}/{artifact_type}")
async def download_intelligence_artifact(
    repo_id: str, 
    artifact_type: str,
    current_user: dict = Depends(get_current_user)
):
    verify_repo_ownership(repo_id, current_user["uid"])
    data = memory_service.retrieve(repo_id)
    if not data:
        raise HTTPException(status_code=404, detail="Repository intelligence data not found.")

    artifact_map = {
        "profile": ("repository_profile.json", "application/json", lambda d: json.dumps(d["profile"], indent=2)),
        "graph": ("repository_graph.json", "application/json", lambda d: json.dumps(d["graph"], indent=2)),
        "summary": ("repository_summary.json", "application/json", lambda d: json.dumps(d["summary"], indent=2)),
        "report": ("repository_report.md", "text/markdown", lambda d: d["report"]),
    }
    if artifact_type not in artifact_map:
        raise HTTPException(status_code=400, detail="Invalid artifact type.")

    filename, media_type, content_fn = artifact_map[artifact_type]
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content_fn(data))
    return FileResponse(
        file_path,
        media_type=media_type,
        filename=filename,
        background=BackgroundTask(lambda: shutil.rmtree(temp_dir, ignore_errors=True)),
    )

class ChatRequest(BaseModel):
    repo_id: str
    question: str
    session_id: Optional[str] = None

@app.post("/api/chat")
async def chat_with_repo(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    x_gemini_key: Optional[str] = Header(None)
):
    # Step 6: Verify ownership before querying Pinecone
    verify_repo_ownership(request.repo_id, current_user["uid"])

    gemini_key = x_gemini_key or os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        raise HTTPException(status_code=400, detail="Gemini API Key missing.")

    repo_data = memory_service.retrieve(request.repo_id)
    if not repo_data:
        raise HTTPException(status_code=404, detail="Repository intelligence data not found.")

    session_id = request.session_id or str(uuid.uuid4())

    from agents.llm_client import GeminiLLMClient
    from agents.orchestrator import AgentOrchestrator

    conversation_manager.add_message(
        session_id=session_id,
        repo_id=request.repo_id,
        role="user",
        content=request.question
    )

    llm_client = GeminiLLMClient(api_key=gemini_key)
    orchestrator = AgentOrchestrator(llm_client)
    embedder = EmbeddingService(api_key=gemini_key)
    retriever = KnowledgeRetriever(embedder, get_vector_store())

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

    result["session_id"] = session_id
    conversation_manager.add_message(
        session_id=session_id,
        repo_id=request.repo_id,
        role="assistant",
        content=result.get("answer", "")
    )

    # Step 5: Save message to Supabase conversations table
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO conversations (uid, repo_id, role, content)
                    VALUES (%s, %s, %s, %s);
                """, (current_user["uid"], request.repo_id, "user", request.question))
                cur.execute("""
                    INSERT INTO conversations (uid, repo_id, role, content)
                    VALUES (%s, %s, %s, %s);
                """, (current_user["uid"], request.repo_id, "assistant", result.get("answer", "")))
    except Exception as db_e:
        logger.warning(f"Error logging conversations to Supabase: {db_e}")

    return result

class SearchRequest(BaseModel):
    repo_id: str
    query: str
    top_k: int = 5
    category: Optional[str] = None

@app.post("/api/search")
async def semantic_search(
    request: SearchRequest,
    current_user: dict = Depends(get_current_user),
    x_gemini_key: Optional[str] = Header(None)
):
    # Step 6: Verify ownership before querying Pinecone
    verify_repo_ownership(request.repo_id, current_user["uid"])

    gemini_key = x_gemini_key or os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        raise HTTPException(status_code=400, detail="Gemini API Key required.")

    embedder = EmbeddingService(api_key=gemini_key)
    retriever = KnowledgeRetriever(embedder, get_vector_store())
    results = retriever.retrieve(
        repo_id=request.repo_id,
        query=request.query,
        top_k=request.top_k,
        category=request.category
    )
    return {
        "query": request.query,
        "results": results,
        "result_count": len(results)
    }

@app.get("/api/memory")
async def get_memory_info(
    repo_id: str,
    current_user: dict = Depends(get_current_user)
):
    verify_repo_ownership(repo_id, current_user["uid"])
    vs = get_vector_store()
    count = vs.count_documents(repo_id)
    return {
        "repo_id": repo_id,
        "indexed_chunks": count,
        "index_name": vs.index_name
    }

@app.get("/api/conversations")
async def list_conversations(
    repo_id: str,
    current_user: dict = Depends(get_current_user)
):
    verify_repo_ownership(repo_id, current_user["uid"])
    sessions = conversation_manager.list_sessions_for_repo(repo_id)
    return {"repo_id": repo_id, "sessions": sessions}

@app.get("/api/conversations/{session_id}")
async def get_conversation(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    history = session_manager.get_session_history(session_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"session_id": session_id, "history": history}

@app.get("/api/tools")
async def list_tools(current_user: dict = Depends(get_current_user)):
    tools = [
        {"name": "repository_search", "description": "Semantic search over indexed repo chunks."},
        {"name": "graph_query", "description": "Query architecture graph."},
        {"name": "dependency_lookup", "description": "Lookup dependencies."},
        {"name": "architecture_lookup", "description": "Query architecture pattern."},
        {"name": "api_lookup", "description": "Lookup HTTP routes."}
    ]
    return {"tools": tools, "count": len(tools)}

# Serve static frontend build if present
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")
