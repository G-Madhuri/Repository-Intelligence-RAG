import os
import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clean_gemini_schema(schema: Any) -> Any:
    """
    Recursively removes 'additionalProperties', '$schema', and 'title' keys from Pydantic schema
    for strict compatibility with Google Gemini Developer API mode.
    """
    if isinstance(schema, dict):
        cleaned = {}
        for key, value in schema.items():
            if key in ["additionalProperties", "$schema", "title"]:
                continue
            cleaned[key] = clean_gemini_schema(value)
        return cleaned
    elif isinstance(schema, list):
        return [clean_gemini_schema(item) for item in schema]
    return schema


# Define Pydantic response schemas
class ProfileSchema(BaseModel):
    project_name: str = Field(description="Name of the software project")
    project_type: str = Field(description="Type of the project, e.g. web app, CLI, library, etc.")
    languages: List[str] = Field(description="Programming languages used in the repository")
    frameworks: List[str] = Field(description="Frameworks used (e.g. Django, FastAPI, React)")
    databases: List[str] = Field(description="Databases detected (e.g. PostgreSQL, Redis, MongoDB)")
    authentication_methods: List[str] = Field(description="Security/authentication methods (e.g. JWT, OAuth, session)")
    major_modules: List[str] = Field(description="Key modules or packages in the codebase")
    api_endpoints: List[str] = Field(description="List of core API routes / endpoints discovered")
    important_files: List[str] = Field(description="Important files for configuring or understanding the app")
    architecture_pattern: str = Field(description="The primary architectural pattern (e.g. MVC, Clean Architecture, Monolith)")
    dependencies: List[str] = Field(description="Main dependencies or libraries used")


class SummarySchema(BaseModel):
    elevator_pitch: str = Field(description="A 2-3 sentence overview of the codebase and its purpose")
    core_features: List[str] = Field(description="List of core features implemented in the repository")
    main_workflows: List[str] = Field(description="Major developer or user workflows identified")
    key_components: List[str] = Field(description="Key code components or classes")
    key_risks: List[str] = Field(description="Potential architectural risks or legacy blocks")
    developer_start_points: List[str] = Field(description="Suggested files or modules where a developer should start reading")


class NodePropertySchema(BaseModel):
    key: str = Field(description="Property key name")
    value: str = Field(description="Property value")


class NodeSchema(BaseModel):
    id: str = Field(description="Unique ID for the node, e.g. the path or the identifier")
    label: str = Field(description="Human-readable label for the node")
    type: str = Field(description="Type of the node (module, api, database, entrypoint, file)")
    properties: List[NodePropertySchema] = Field(default_factory=list, description="List of key-value properties")


class EdgeSchema(BaseModel):
    source: str = Field(description="ID of the source node")
    target: str = Field(description="ID of the target node")
    type: str = Field(description="Type of relation (imports, calls, data_flow, ownership)")
    label: str = Field(description="Human-readable label for the relation")


class EntryPointSchema(BaseModel):
    file_path: str = Field(description="Path to the execution entry point file")
    type: str = Field(description="Type of execution path, e.g. script, dev server, wsgi")
    description: str = Field(description="Description of what this entry point runs")


class BusinessFlowSchema(BaseModel):
    flow_name: str = Field(description="Name of the business process flow")
    description: str = Field(description="Summary of what the workflow does")
    steps: List[str] = Field(description="Ordered list of node IDs involved in the workflow")


class CriticalPathSchema(BaseModel):
    path_name: str = Field(description="Name of the performance-critical path")
    description: str = Field(description="Explanation of why this path is critical")
    nodes: List[str] = Field(description="List of node IDs in this path")


class ConceptSchema(BaseModel):
    name: str = Field(description="Conceptual area, e.g. State Management, Caching")
    description: str = Field(description="How this concept is implemented")
    files: List[str] = Field(description="Files corresponding to this concept")


class GraphSchema(BaseModel):
    nodes: List[NodeSchema] = Field(description="Nodes in the topology graph")
    edges: List[EdgeSchema] = Field(description="Directed edges in the topology graph")
    entry_points: List[EntryPointSchema] = Field(description="Identified application entry points")
    business_flows: List[BusinessFlowSchema] = Field(description="Primary user/business flows")
    critical_paths: List[CriticalPathSchema] = Field(description="Performance-critical execution paths")
    concepts: List[ConceptSchema] = Field(description="Core concepts mapped to code files")


class AnalysisResponse(BaseModel):
    report: str = Field(description="A beautifully formatted Markdown Repository Intelligence Report")
    profile: ProfileSchema = Field(description="Structured metadata profiling the project tech stack and components")
    summary: SummarySchema = Field(description="High-level summaries and onboarding metadata")
    graph: GraphSchema = Field(description="Topology graph of file and module relations")


def select_important_files(files: List[Dict[str, Any]], max_tokens: int = 150000) -> List[Dict[str, Any]]:
    """
    Selects files that are most structurally important first to prevent exceeding prompt token limits.
    """
    def get_file_priority(f: Dict[str, Any]) -> int:
        path_lower = f["path"].lower()
        parts = [p.strip() for p in path_lower.split("/") if p.strip()]
        filename = parts[-1] if parts else ""
        
        if filename in ["readme.md", "readme.rst", "readme.txt"]: return 1
        if filename in ["package.json", "requirements.txt", "pyproject.toml", "cargo.toml", "go.mod", "pom.xml", "build.gradle", "dockerfile"]: return 2
        if filename in ["main.py", "app.py", "index.js", "main.go", "server.js", "app.ts", "index.ts", "main.rs"]: return 3
        
        for part in parts:
            if part in ["routes", "api", "controllers", "services", "models", "src"]: return 4
            
        if filename.endswith((".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".java", ".rs", ".cpp", ".c", ".h")): return 5
        return 10

    sorted_files = sorted(files, key=get_file_priority)
    selected = []
    current_chars = 0
    max_chars = max_tokens * 4

    for f in sorted_files:
        content = f.get("content", "")
        if not content: continue
        
        if len(content) > 50000:
            logger.info(f"Skipping file content for {f['path']} - file size is larger than 50KB.")
            continue

        if current_chars + len(content) > max_chars:
            logger.info(f"Skipping content of file {f['path']} due to context size limit.")
            continue

        selected.append(f)
        current_chars += len(content)

    return selected


async def analyze_repository(
    repo_name: str,
    tree_structure: Dict[str, Any],
    static_profile: Dict[str, Any],
    flat_files: List[Dict[str, Any]],
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calls Gemini 2.5 Flash using google-genai SDK to analyze codebase context
    and return structured JSON matching AnalysisResponse schema.
    """
    gemini_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        raise Exception("Gemini API key is required. Please set GEMINI_API_KEY in environment.")

    from google import genai
    client = genai.Client(api_key=gemini_key)

    selected_files = select_important_files(flat_files)
    formatted_code_blocks = []
    for f in selected_files:
        formatted_code_blocks.append(f"--- FILE: {f['path']} ---\n{f['content']}")
    
    formatted_code = "\n\n".join(formatted_code_blocks)

    tree_str = json.dumps(tree_structure, indent=2)
    profile_str = json.dumps(static_profile, indent=2)

    prompt = f"""
You are an expert Principal Software Engineer analyzing the source code repository of the project named '{repo_name}'.

Your goal is to perform a deep structural and conceptual analysis of this repository, thinking like a senior engineer who has spent 30 minutes reading the codebase. Do not just summarize files. Infer business logic, workflows, entrypoints, database models, user flows, service interactions, authentication paths, and key concepts.

Below is the repository context:

1. STATIC PROFILE:
{profile_str}

2. FILE DIRECTORY STRUCTURE:
{tree_str}

3. PRIMARY CODE FILES CONTENT:
{formatted_code}

You must analyze the repository context and return the structured outputs matching the schema.
"""

    try:
        logger.info("Sending request to Gemini via google-genai SDK with clean response_schema...")
        
        # Clean Pydantic schema for strict Gemini Developer API compatibility
        clean_schema = clean_gemini_schema(AnalysisResponse.model_json_schema())

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': clean_schema,
                'temperature': 0.2
            }
        )
        
        response_text = response.text
        if not response_text:
            raise Exception("Gemini returned an empty response text.")
        
        result_json = json.loads(response_text)
        return result_json
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode response from Gemini as JSON: {e}")
        raise HTTPException(status_code=500, detail=f"Gemini API returned invalid JSON structure: {str(e)}")
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error communicating with Gemini: {error_msg}")
        if "401" in error_msg or "UNAUTHENTICATED" in error_msg:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail="Gemini API Key Authentication Failed (401). Please check your GEMINI_API_KEY in backend/.env."
            )
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Gemini analysis execution failed: {error_msg}")


