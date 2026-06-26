import asyncio
import os
import sys
from typing import Dict, Any, Type
from pydantic import BaseModel

# Add backend directory to path if needed
sys.path.append(os.path.dirname(__file__))

from agents.llm_client import LLMClient
from agents.orchestrator import AgentOrchestrator
from agents.planner_agent import PlannerDecision
from agents.base_agent import AgentResponseSchema
from agents.response_synthesizer import SynthesizedResponse

class MockLLMClient(LLMClient):
    """
    Mock LLM client to run validation tests without hitting Gemini API endpoints.
    """
    def generate_json(
        self,
        prompt: str,
        response_schema: Type[BaseModel],
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        print(f"[MockLLMClient] Called with schema: {response_schema.__name__}")
        
        if response_schema == PlannerDecision:
            return {
                "selected_agents": ["SecurityAgent", "ApiAgent"],
                "execution_order": [["SecurityAgent", "ApiAgent"]],
                "reasoning": "Query is about endpoints and credentials."
            }
        
        elif response_schema == AgentResponseSchema:
            prompt_lower = prompt.lower()
            if "security" in prompt_lower:
                return {
                    "agent": "SecurityAgent",
                    "confidence": 0.95,
                    "answer": "Checked endpoints. Found jwt authentication.",
                    "citations": ["backend/main.py:L48"],
                    "reasoning": ["Parsed authentication middleware."]
                }
            elif "api" in prompt_lower:
                return {
                    "agent": "ApiAgent",
                    "confidence": 0.90,
                    "answer": "Endpoints found: POST /api/analyze-url.",
                    "citations": ["backend/main.py:L64"],
                    "reasoning": ["Scanned fastapi routes."]
                }
            else:
                return {
                    "agent": "GenericAgent",
                    "confidence": 0.80,
                    "answer": "Generic analysis.",
                    "citations": [],
                    "reasoning": []
                }
                
        elif response_schema == SynthesizedResponse:
            return {
                "summary": "Coherent combined view of authentication and API endpoints.",
                "detailed_explanation": "Combined: The app has jwt authentication on routes like POST /api/analyze-url.",
                "agent_contributions": [
                    "SecurityAgent: Analyzed JWT usage.",
                    "ApiAgent: Listed endpoints."
                ],
                "confidence_score": 0.93
            }
            
        return {}

async def run_tests():
    print("=== Running Integration Tests for Phase 2 Agent Architecture ===")
    
    # Setup mock data
    profile = {
        "project_name": "Test Project",
        "project_type": "web app",
        "languages": ["Python"],
        "frameworks": ["FastAPI"],
        "databases": [],
        "authentication_methods": ["JWT"],
        "major_modules": ["main"],
        "api_endpoints": ["/api/health", "/api/analyze-url"],
        "important_files": ["main.py"],
        "architecture_pattern": "Monolithic",
        "dependencies": ["fastapi", "uvicorn"]
    }
    
    graph = {
        "nodes": [{"id": "main.py", "label": "main.py", "type": "file", "properties": {}}],
        "edges": [],
        "entry_points": [{"file_path": "main.py", "type": "uvicorn", "description": "Start app"}],
        "business_flows": [],
        "critical_paths": [],
        "concepts": []
    }
    
    summary = {
        "elevator_pitch": "A test repository scanning tool.",
        "core_features": ["Cloning", "Scanning"],
        "main_workflows": [],
        "key_components": [],
        "key_risks": [],
        "developer_start_points": ["main.py"]
    }
    
    report = "# Test Intelligence Report\nThis is a mock repository report."
    
    query = "How is security and routing configured?"

    mock_client = MockLLMClient()
    orchestrator = AgentOrchestrator(mock_client)
    
    print("\nExecuting orchestrator...")
    result = await orchestrator.execute(profile, graph, summary, report, query, repo_id="test_repo")
    
    print("\n--- Test Result ---")
    print(f"Synthesized Answer: {result['answer']}")
    print(f"Agents Used: {result['agents_used']}")
    print(f"Confidence Score: {result['confidence']}")
    print(f"Citations/References: {result['references']}")
    print(f"Timeline Steps count: {len(result['timeline'])}")
    print(f"Total Time MS: {result['total_time_ms']}ms")
    print("-------------------")
    
    # Validate result fields
    assert result['answer'] != ""
    assert "SecurityAgent" in result['agents_used']
    assert "ApiAgent" in result['agents_used']
    assert result['confidence'] == 0.93
    assert len(result['references']) > 0
    assert len(result['timeline']) == 4  # Planner + 2 Parallel Agents + Synthesizer
    print("\nIntegrity assertion checks passed successfully!")

    # Validate fallback behavior when synthesized answer is empty
    print("\nTesting fallback behavior for empty synthesized answer...")
    def generate_json_with_empty_answer(prompt: str, response_schema: Type[BaseModel], temperature: float = 0.2) -> Dict[str, Any]:
        if response_schema == PlannerDecision:
            return {
                "selected_agents": ["SecurityAgent", "ApiAgent"],
                "execution_order": [["SecurityAgent", "ApiAgent"]],
                "reasoning": "Query is about endpoints and credentials."
            }
        elif response_schema == AgentResponseSchema:
            prompt_lower = prompt.lower()
            if "security agent" in prompt_lower or "architecture agent" in prompt_lower or "quality agent" in prompt_lower or "onboarding agent" in prompt_lower:
                return {
                    "agent": "SecurityAgent",
                    "confidence": 0.95,
                    "answer": "Checked endpoints. Found jwt authentication.",
                    "citations": ["backend/main.py:L48"],
                    "reasoning": ["Parsed authentication middleware."]
                }
            elif "api agent" in prompt_lower or "api" in prompt_lower:
                return {
                    "agent": "ApiAgent",
                    "confidence": 0.90,
                    "answer": "Endpoints found: POST /api/analyze-url.",
                    "citations": ["backend/main.py:L64"],
                    "reasoning": ["Scanned fastapi routes."]
                }
            else:
                return {
                    "agent": "GenericAgent",
                    "confidence": 0.80,
                    "answer": "Generic analysis.",
                    "citations": [],
                    "reasoning": []
                }
        elif response_schema == SynthesizedResponse:
            return {
                "summary": "Fallback summary compiled from individual agents.",
                "detailed_explanation": "",
                "agent_contributions": [
                    "SecurityAgent: Analyzed JWT usage.",
                    "ApiAgent: Listed endpoints."
                ],
                "confidence_score": 0.50
            }
        return {}

    mock_client.generate_json = generate_json_with_empty_answer  # type: ignore
    fallback_result = await orchestrator.execute(profile, graph, summary, report, query, repo_id="test_repo")
    assert fallback_result['answer'] != ""
    assert "SecurityAgent" in fallback_result['answer']
    assert "ApiAgent" in fallback_result['answer']
    print("Fallback behavior validation passed successfully!")

if __name__ == "__main__":
    asyncio.run(run_tests())
