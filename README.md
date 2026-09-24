---
title: Repository Intelligence Layer
emoji: 🔍
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# 🔍 Repository Intelligence Layer

### AI-powered codebase analysis with multi-agent RAG

Turn any GitHub repository or ZIP archive into structured intelligence (an architecture report, a tech-stack profile, a dependency graph), then ask questions about it through a team of specialist AI agents grounded in the actual code.

> 🌐 **Live Demo:** https://huggingface.co/spaces/G-Madhuri/Software_Engineer_Agent

---

## 🚀 Overview

Getting to grips with an unfamiliar codebase is slow. You read the README, hunt for entry points, trace imports and work out the API surface and auth model.

This project automates that first pass:

1. **Ingest:** clone a GitHub repo (public, or private with a PAT) or upload a ZIP into an isolated temporary workspace.
2. **Static analysis:** walk the file tree, parse manifests (`package.json`, `requirements.txt`, `go.mod`, `Cargo.toml`), detect languages, frameworks, databases and infrastructure, and build an import graph.
3. **LLM reasoning:** send the most important files, together with the static profile, to **Gemini 2.5 Flash** using a strict JSON schema. It returns a report, a profile, a summary and an architecture graph.
4. **Index:** chunk the report, the extracted knowledge and the source code, embed them with **Pinecone Inference (`llama-text-embed-v2`)**, and store them in a per-repository **Pinecone** namespace.
5. **Chat:** a **Planner agent** chooses which specialist agents and tools to run. The agents run in parallel with the retrieved code as context, and a **Synthesizer** merges their output into one answer with citations, a confidence score and a full execution timeline.

Users sign in with **Supabase Auth**. Every repository's data expires automatically after **1 hour**.

---

## ✨ Features

- 🔐 **Supabase authentication:** email/password sign-in, with the JWT verified server-side on every API call
- 📦 **GitHub URL or ZIP upload:** private repos via Personal Access Token, and ZIP extraction protected against path traversal (zip-slip)
- 🧭 **Static profiling:** languages, frameworks, databases, package managers and infrastructure (Docker, CI, Kubernetes, Serverless)
- 🧠 **Gemini 2.5 Flash analysis:** schema-validated Markdown report, profile, summary and architecture graph (entry points, business flows, critical paths, concepts)
- 🕸️ **Interactive architecture graph:** layered SVG view with business-flow and critical-path highlighting
- 🤖 **Multi-agent AI assistant:** Planner, then 6 specialists (Architecture, Security, API, Dependency, Quality, Onboarding), then a Synthesizer
- 🔎 **Knowledge Explorer:** semantic search with category filters, index statistics and conversation history
- 🧾 **Explainable answers:** planner reasoning, per-agent latency and confidence, retrieved code chunks and references
- ⏱️ **1-hour data TTL:** a background job purges expired repositories from Pinecone and Postgres
- 🐳 **Single-container deployment:** FastAPI serves both the API and the built React app (Hugging Face Spaces)

---

## 🏗️ Architecture

```mermaid
flowchart LR
  subgraph Client
    UI[React + Vite SPA]
  end
  subgraph Backend["FastAPI (modular monolith)"]
    Auth[Supabase JWT check]
    Ingest[Scanner → Profiler → Graph Builder]
    LLM[Gemini Analyzer]
    Index[Knowledge Index Builder]
    Orch[Agent Orchestrator]
    Sched[APScheduler TTL purge]
  end
  subgraph Services
    SB[(Supabase Auth + Postgres)]
    GH[GitHub API / git]
    GEM[Gemini 2.5 Flash]
    PC[(Pinecone + Inference)]
    LS[LangSmith]
  end

  UI -- Bearer JWT --> Auth --> SB
  UI --> Ingest --> GH
  Ingest --> LLM --> GEM
  LLM --> Index --> PC
  UI --> Orch
  Orch --> PC
  Orch --> GEM
  Orch -. traces .-> LS
  Sched --> SB
  Sched --> PC
```

### Chat pipeline

```
Question
  → PlannerAgent (decides memory / semantic search / tools / agents / execution order)
  → Conversation memory + Pinecone top-k retrieval + cached tool lookups
  → Specialist agents run in parallel stages (with retries)
  → ResponseSynthesizer (merges, dedupes, scores confidence)
  → Answer + citations + timeline
```

Every stage has a fallback. If the planner fails, all agents run. Failed agents are retried and then skipped. If the synthesizer fails, the agents' answers are concatenated instead.

---

## 🛠️ Tech Stack

| Layer | Technologies |
|---|---|
| Frontend | React 18, Vite 5, Supabase JS, marked, lucide-react, custom CSS |
| Backend | Python, FastAPI, Uvicorn, Pydantic v2, httpx, APScheduler |
| AI / LLM | Gemini 2.5 Flash (`google-genai` + LangChain `langchain-google-genai`), structured output |
| RAG | Pinecone (serverless index, namespace per repo), Pinecone Inference `llama-text-embed-v2` (1024-d) |
| Auth & DB | Supabase Auth, Supabase PostgreSQL (psycopg2), Row Level Security |
| Observability | LangSmith tracing, Python logging |
| Deployment | Docker (multi-stage), Hugging Face Spaces, docker-compose + nginx for local dev |

---

## 📁 Project Structure

```
├── backend/
│   ├── main.py                # FastAPI app, routes, TTL scheduler, static file serving
│   ├── auth.py                # Supabase JWT verification dependency
│   ├── migrate_supabase.py    # Postgres schema + RLS policies
│   ├── services/              # Scanner, profiler, graph builder, Gemini analyzer, artifact store
│   ├── memory/                # Embeddings, Pinecone vector store, retriever, sessions, cache
│   ├── agents/                # LLM client, planner, 6 specialists, synthesizer, orchestrator
│   ├── tools/                 # Tool registry (search, graph, dependency, architecture, API lookups)
│   └── requirements.txt
├── frontend/
│   ├── src/App.jsx            # Auth session + app state machine
│   ├── src/components/        # InputForm, Dashboard, GraphViewer, RepositoryAssistant, KnowledgeExplorer, ...
│   └── vite.config.js         # Dev proxy /api → backend
├── Dockerfile                 # Unified build for Hugging Face Spaces (port 7860)
└── docker-compose.yml         # Local split stack (backend + nginx frontend)
```

---

## ⚙️ Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- Git (the backend clones repositories)
- Accounts and keys for **Gemini**, **Pinecone** and **Supabase** (LangSmith is optional)

### 1. Clone

```bash
git clone https://github.com/G-Madhuri/Repository-Intelligence-RAG.git
cd Repository-Intelligence-RAG
```

### 2. Configure environment

Create `backend/.env`:

```env
# LLM
GEMINI_API_KEY=your_gemini_api_key

# Vector database
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=your_index_name        # 1024-dim index for llama-text-embed-v2

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key
DATABASE_URL=postgresql://user:password@host:5432/postgres

# Optional
CORS_ORIGINS=http://localhost:5173
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_key
LANGSMITH_PROJECT=repository-intelligence
```

For the frontend, you can optionally create `frontend/.env`:

```env
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
# VITE_API_URL=            # leave empty to use the Vite proxy
# VITE_API_PROXY=http://localhost:8000
```

### 3. Create the database tables

```bash
cd backend
pip install -r requirements.txt
python migrate_supabase.py
```

This creates the `users`, `repos`, `jobs` and `conversations` tables and enables Row Level Security.

### 4. Run the backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 5. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173, sign up or sign in, and analyze a repository.

---

## 🐳 Docker

**Single container** (the same image that runs on Hugging Face Spaces):

```bash
docker build -t repository-intelligence .
docker run -p 7860:7860 --env-file backend/.env repository-intelligence
```

Then open http://localhost:7860.

**Split stack** (backend plus an nginx frontend):

```bash
docker compose up --build
```

Then open http://localhost:5173.

---

## 🔌 API Endpoints

Every `/api/*` route except the health check needs `Authorization: Bearer <supabase_access_token>`.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Health check (public) |
| POST | `/api/analyze-url` | Analyze a GitHub repo: `{ "url": "...", "token": "optional PAT" }` |
| POST | `/api/analyze-zip` | Analyze an uploaded `.zip` (multipart `file`) |
| POST | `/api/chat` | Multi-agent Q&A: `{ "repo_id", "question", "session_id?" }` |
| POST | `/api/search` | Semantic search: `{ "repo_id", "query", "top_k", "category?" }` |
| GET | `/api/download/{repo_id}/{type}` | Download `report`, `profile`, `summary` or `graph` |
| GET | `/api/memory?repo_id=` | Number of indexed chunks |
| GET | `/api/conversations?repo_id=` | Chat sessions for a repo |
| GET | `/api/conversations/{session_id}` | Session history |
| GET | `/api/tools` | Available agent tools |

Interactive API docs are available at `/docs`.

---

## 📊 Generated Artifacts

| Artifact | Contents |
|---|---|
| `repository_report.md` | Full Markdown intelligence report |
| `repository_profile.json` | Languages, frameworks, databases, auth methods, modules, API endpoints, architecture pattern, dependencies |
| `repository_summary.json` | Elevator pitch, core features, workflows, key components, risks, where to start reading |
| `repository_graph.json` | Nodes, edges, entry points, business flows, critical paths, concepts |

---

## 🔒 Security

- Supabase JWT verified server-side (`auth.get_user`) on every protected route
- Per-repository ownership checks, plus Row Level Security policies in Postgres
- Per-repository Pinecone namespaces for tenant isolation
- ZIP path-traversal (zip-slip) protection
- GitHub PAT redacted from error output and never stored; temporary workspaces deleted after each analysis
- Parameterized SQL queries; clone target restricted to `github.com/<owner>/<repo>`
- Automatic 1-hour data expiry
- Secrets kept in environment variables (never commit `.env`)

---

## 🗺️ Roadmap

- [ ] Background job queue with real-time progress (SSE)
- [ ] Stateless backend (object storage for artifacts, Redis cache) for horizontal scaling
- [ ] Rate limiting and upload size limits
- [ ] Sanitized Markdown rendering (DOMPurify)
- [ ] Analysis caching by commit SHA
- [ ] End-to-end LangSmith traces and evaluation datasets
- [ ] CI pipeline (lint, mocked-LLM tests, image build)

---

## 👩‍💻 Author

**G. Madhuri**: [GitHub](https://github.com/G-Madhuri) · [Hugging Face](https://huggingface.co/G-Madhuri)

⭐ If you find this project useful, consider giving it a star!
