import os
import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Define Pydantic response schemas to guarantee valid JSON structure from Gemini
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


class NodeSchema(BaseModel):
    id: str = Field(description="Unique ID for the node, e.g. the path or the identifier")
    label: str = Field(description="Human-readable label for the node")
    type: str = Field(description="Type of the node (module, api, database, entrypoint, file)")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Custom properties metadata")


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
    Selects files that are most structurally important first (README, manifests, entry points,
    routes, controllers, services, models) to prevent exceeding prompt token/context limits on
    large repositories.
    """
    def get_file_priority(f: Dict[str, Any]) -> int:
        path_lower = f["path"].lower()
        parts = [p.strip() for p in path_lower.split("/") if p.strip()]
        filename = parts[-1] if parts else ""
        
        # Priority 0: Critical manifests, config registries and high-level summaries
        p0_exact = {
            "readme.md", "readme.txt", "package.json", "requirements.txt", 
            "pyproject.toml", "go.mod", "cargo.toml", "pom.xml", "build.gradle"
        }
        if filename in p0_exact:
            return 0
            
        # Priority 1: Key execution entry points
        p1_exact = {
            "main.py", "app.py", "server.js", "index.js", "wsgi.py", "asgi.py"
        }
        if filename in p1_exact:
            return 1
            
        # Priority 2: Key architectural components / directories
        p2_dirs = {
            "routes", "controllers", "services", "models", "api", "handlers", "views"
        }
        if any(d in parts for d in p2_dirs):
            return 2
            
        # Priority 3: Other general code files
        return 3

    sorted_files = sorted(files, key=get_file_priority)
    
    selected = []
    current_size = 0
    # Estimate: roughly 4 characters per token
    char_limit = max_tokens * 4
    
    for f in sorted_files:
        content_len = len(f.get("content", ""))
        # Filter files larger than 50KB to protect context window spacing
        if f["size"] > 50 * 1024:
            logger.info(f"Skipping file content for {f['path']} - file size is larger than 50KB.")
            continue
            
        if current_size + content_len <= char_limit:
            selected.append(f)
            current_size += content_len
        else:
            logger.info(f"Skipping content of file {f['path']} due to context size limit.")
            
    return selected


async def analyze_repository(
    repo_name: str,
    tree_structure: Dict[str, Any],
    static_profile: Dict[str, Any],
    flat_files: List[Dict[str, Any]],
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates a Repository Intelligence Report, profile.json, summary.json, and graph.json
    using Google Gemini via the new google-genai SDK.
    """
    # API Key selection: Try parameter first, then environment variable
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ValueError("Gemini API Key is missing. Please configure it in the backend or frontend.")
    
    # Import and configure the new google-genai SDK
    from google import genai
    
    client = genai.Client(api_key=key)
    
    # Select important files content to keep under budget
    context_files = select_important_files(flat_files)
    
    # Format files for prompt ingestion
    formatted_code = ""
    for f in context_files:
        formatted_code += f"\n\n--- File: {f['path']} ---\n"
        formatted_code += f.get("content", "")
        formatted_code += "\n--- End File ---"

    # Convert tree structure to JSON string
    tree_str = json.dumps(tree_structure, indent=2)
    # Convert static profile to JSON string
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
        logger.info("Sending request to Gemini via google-genai SDK with response_schema...")
        
        # Use the new client-based API with the response_schema configuration parameter
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': AnalysisResponse,
                'temperature': 0.2
            }
        )
        
        # Parse the structured JSON response
        response_text = response.text
        if not response_text:
            raise Exception("Gemini returned an empty response. Please check your API key and quota.")
        
        result_json = json.loads(response_text)
        return result_json
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode response from Gemini as JSON: {e}")
        raise Exception(f"Gemini API returned an invalid JSON response structure. Please retry. Error: {str(e)}")
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error communicating with Gemini: {error_msg}")
        # Provide more helpful error messages
        if "API_KEY_INVALID" in error_msg or "401" in error_msg:
            raise Exception(
                "Invalid Gemini API Key. Please get a valid key from https://aistudio.google.com/apikey "
                "and set it in the .env file or pass it via the frontend."
            )
        elif "RESOURCE_EXHAUSTED" in error_msg or "429" in error_msg:
            raise Exception(
                "Gemini API rate limit exceeded. Please wait a moment and try again, "
                "or upgrade your API quota at https://aistudio.google.com."
            )
        raise Exception(f"Gemini analysis execution failed: {error_msg}")
