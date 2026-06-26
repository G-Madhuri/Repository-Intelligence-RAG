import json
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from agents.base_agent import BaseAgent

class PlannerDecision(BaseModel):
    retrieve_memory: bool = Field(
        description="Whether to retrieve past conversation history or context for the current query."
    )
    run_semantic_search: bool = Field(
        description="Whether to query the vector database for matching chunks from the codebase."
    )
    invoke_tools: List[str] = Field(
        description="List of tool names to invoke, from: ['repository_search', 'graph_query', 'dependency_lookup', 'file_reader', 'architecture_lookup', 'api_lookup']."
    )
    run_agents: bool = Field(
        description="Whether specialized agents should be executed."
    )
    selected_agents: List[str] = Field(
        description="List of agent names selected to run if run_agents is true, from: ['ArchitectureAgent', 'SecurityAgent', 'ApiAgent', 'DependencyAgent', 'QualityAgent', 'OnboardingAgent']."
    )
    execution_order: List[List[str]] = Field(
        description="Execution order for agents (e.g., [['SecurityAgent', 'ApiAgent'], ['ArchitectureAgent']]) if run_agents is true."
    )
    synthesize_final_answer: bool = Field(
        description="Whether the response synthesizer should combine everything into the final answer. Set to True unless a direct tool/search result is sufficient."
    )
    reasoning: str = Field(
        description="Explanation of why these pipeline decisions and agent executions were chosen."
    )

class PlannerAgent(BaseAgent):
    async def run(
        self,
        profile: Dict[str, Any],
        graph: Dict[str, Any],
        summary: Dict[str, Any],
        report: str,
        query: str
    ) -> Dict[str, Any]:
        prompt = f"""
You are the Agent Orchestration Planner. Your task is to analyze the user's query and decide the best execution pipeline to resolve it.

The execution pipeline consists of:
1. retrieve_memory: Fetching past chat history/turns.
2. run_semantic_search: Finding relevant code snippets via vector embeddings.
3. invoke_tools: Executing direct lookup/search tools.
4. run_agents: Launching specialized agents in parallel or sequential stages.
5. synthesize_final_answer: Combining all info into a clean final markdown explanation.

Available Tools:
- repository_search: Semantic search over indexed repo chunks.
- graph_query: Query dependency graph, business flows, entry points.
- dependency_lookup: Look up project languages, frameworks, packages.
- file_reader: Retrieve specific source code file content.
- architecture_lookup: Query high-level architecture pattern and major folders.
- api_lookup: Look up HTTP endpoints, authentication details.

Available Agents:
1. ArchitectureAgent: Focuses on architectural patterns, component interaction, data flow, component responsibilities, and business flows.
2. SecurityAgent: Focuses on authentication, authorization, API keys, secrets, security risks, vulnerability findings, and unsafe practices.
3. ApiAgent: Focuses on endpoints, routes, HTTP methods, request/response models, and external APIs.
4. DependencyAgent: Focuses on libraries, frameworks, cloud stack, dependencies, and infrastructure setup.
5. QualityAgent: Focuses on complexity, maintainability, dead code, refactoring suggestions, and testing hints.
6. OnboardingAgent: Focuses on developer onboarding walkthrough, where to start reading, and execution setup.

Repository Profile:
{json.dumps(profile, indent=2)}

Repository Summary:
{json.dumps(summary, indent=2)}

User Query:
{query}

Determine:
1. Which pipeline components should run (retrieve_memory, run_semantic_search, invoke_tools, run_agents, synthesize_final_answer).
2. Which agents and tools are needed and their execution plan.
3. The reasoning behind your plan.

Return your decision in structured JSON format matching the schema.
"""
        return await self._call_llm_json(prompt, PlannerDecision, temperature=0.1)
