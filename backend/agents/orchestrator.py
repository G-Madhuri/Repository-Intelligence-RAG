import time
import asyncio
import logging
import json
from typing import Dict, Any, List, Optional
from agents.llm_client import LLMClient
from agents.planner_agent import PlannerAgent
from agents.architecture_agent import ArchitectureAgent
from agents.security_agent import SecurityAgent
from agents.api_agent import ApiAgent
from agents.dependency_agent import DependencyAgent
from agents.quality_agent import QualityAgent
from agents.onboarding_agent import OnboardingAgent
from agents.response_synthesizer import ResponseSynthesizer
from tools.tool_registry import tool_registry, setup_default_registry
from memory.memory_cache import memory_cache
from memory.conversation_manager import conversation_manager

logger = logging.getLogger("orchestrator")

class AgentOrchestrator:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.planner = PlannerAgent(llm_client)
        self.synthesizer = ResponseSynthesizer(llm_client)
        
        # Register specialized agents
        self.agents = {
            "ArchitectureAgent": ArchitectureAgent(llm_client),
            "SecurityAgent": SecurityAgent(llm_client),
            "ApiAgent": ApiAgent(llm_client),
            "DependencyAgent": DependencyAgent(llm_client),
            "QualityAgent": QualityAgent(llm_client),
            "OnboardingAgent": OnboardingAgent(llm_client)
        }

    async def execute(
        self,
        profile: Dict[str, Any],
        graph: Dict[str, Any],
        summary: Dict[str, Any],
        report: str,
        query: str,
        repo_id: str,
        session_id: Optional[str] = None,
        vector_store: Optional[Any] = None,
        retriever: Optional[Any] = None
    ) -> Dict[str, Any]:
        timeline = []
        agents_used = []
        start_total = time.time()

        # Initialize tools registry if empty and vector dependencies are available
        if not tool_registry.list_tools() and vector_store and retriever:
            setup_default_registry(vector_store, retriever)

        # 1. Run Planner Agent to decide execution steps
        logger.info(f"Running PlannerAgent for query: '{query}'")
        planner_start = time.time()
        try:
            planner_res = await self.planner.run(profile, graph, summary, report, query)
            planner_latency = time.time() - planner_start
            logger.info(f"PlannerAgent completed in {planner_latency:.2f}s. Plan: {planner_res}")
            timeline.append({
                "agent": "PlannerAgent",
                "execution_time_ms": int(planner_latency * 1000),
                "status": "success",
                "message": f"Pipeline: memory={planner_res.get('retrieve_memory')}, search={planner_res.get('run_semantic_search')}, tools={planner_res.get('invoke_tools')}, agents={planner_res.get('selected_agents')}"
            })
        except Exception as e:
            planner_latency = time.time() - planner_start
            logger.error(f"PlannerAgent failed: {e}")
            timeline.append({
                "agent": "PlannerAgent",
                "execution_time_ms": int(planner_latency * 1000),
                "status": "failure",
                "message": f"Planner failed: {str(e)}"
            })
            # Fallback plan: enable all pipeline elements and run all agents
            planner_res = {
                "retrieve_memory": True,
                "run_semantic_search": True,
                "invoke_tools": [],
                "run_agents": True,
                "selected_agents": list(self.agents.keys()),
                "execution_order": [list(self.agents.keys())],
                "synthesize_final_answer": True,
                "reasoning": "Fallback plan due to planner failure."
            }

        retrieve_memory = planner_res.get("retrieve_memory", True)
        run_semantic_search = planner_res.get("run_semantic_search", True)
        invoke_tools = planner_res.get("invoke_tools", [])
        run_agents = planner_res.get("run_agents", True)
        selected_agents = planner_res.get("selected_agents", [])
        execution_order = planner_res.get("execution_order", [])
        synthesize_final_answer = planner_res.get("synthesize_final_answer", True)

        # 2. Retrieve Memory if requested
        memory_context = ""
        if retrieve_memory and session_id:
            logger.info(f"Retrieving conversation memory for session {session_id}")
            mem_start = time.time()
            session = conversation_manager.get_session(session_id)
            if session and session.history:
                past_turns = []
                for msg in session.history[:-1]:  # Exclude current question which was already added
                    past_turns.append(f"{msg.role.capitalize()}: {msg.content}")
                memory_context = "\n".join(past_turns)
            timeline.append({
                "agent": "MemoryRetrieval",
                "execution_time_ms": int((time.time() - mem_start) * 1000),
                "status": "success",
                "message": "Retrieved past turns" if memory_context else "No past turns found"
            })

        # 3. Run Semantic Search if requested
        search_results = []
        if run_semantic_search and retriever:
            logger.info("Running semantic search retrieval")
            search_start = time.time()
            try:
                search_results = retriever.retrieve(repo_id=repo_id, query=query, top_k=5)
                timeline.append({
                    "agent": "SemanticSearch",
                    "execution_time_ms": int((time.time() - search_start) * 1000),
                    "status": "success",
                    "message": f"Found {len(search_results)} relevant chunks"
                })
            except Exception as e:
                logger.error(f"Semantic search failed: {e}")
                timeline.append({
                    "agent": "SemanticSearch",
                    "execution_time_ms": int((time.time() - search_start) * 1000),
                    "status": "failure",
                    "message": str(e)
                })

        # 4. Invoke Tools (with caching) if requested
        tool_outputs = {}
        if invoke_tools:
            logger.info(f"Invoking tools: {invoke_tools}")
            tool_start = time.time()
            for tool_name in invoke_tools:
                # Check memory cache first
                cache_key = f"tool:{repo_id}:{tool_name}:{query}"
                cached_res = memory_cache.get(cache_key)
                if cached_res is not None:
                    logger.info(f"Cache hit for tool '{tool_name}'")
                    tool_outputs[tool_name] = cached_res
                else:
                    logger.info(f"Cache miss for tool '{tool_name}'. Executing...")
                    res = tool_registry.execute_tool(tool_name, repo_id=repo_id, query=query)
                    memory_cache.set(cache_key, res, ttl=300) # Cache for 5 mins
                    tool_outputs[tool_name] = res
            timeline.append({
                "agent": "ToolInvocation",
                "execution_time_ms": int((time.time() - tool_start) * 1000),
                "status": "success",
                "message": f"Executed {len(tool_outputs)} tools"
            })

        # 5. Run Specialized Agents if requested
        agent_responses = []
        if run_agents and selected_agents:
            # Construct augmented query containing retrieved context and tool outputs
            augmented_context_parts = []
            if memory_context:
                augmented_context_parts.append(f"--- Conversation History ---\n{memory_context}")
            if search_results:
                search_text = "\n\n".join(
                    f"[Relevant Code Chunk | similarity={r['similarity']:.2f}]\n{r['content']}"
                    for r in search_results
                )
                augmented_context_parts.append(f"--- Codebase Semantic Search Results ---\n{search_text}")
            if tool_outputs:
                tools_text = json.dumps(tool_outputs, indent=2)
                augmented_context_parts.append(f"--- Direct Tool Outputs ---\n{tools_text}")

            augmented_query = query
            if augmented_context_parts:
                augmented_query = f"{query}\n\n" + "\n\n".join(augmented_context_parts)

            for stage_idx, stage in enumerate(execution_order):
                tasks = []
                agent_names = []
                
                for agent_name in stage:
                    if agent_name in self.agents and agent_name in selected_agents:
                        agent_names.append(agent_name)
                        tasks.append(self._run_agent_with_retry(agent_name, profile, graph, summary, report, augmented_query))

                if not tasks:
                    continue

                logger.info(f"Executing Stage {stage_idx + 1} with agents in parallel: {agent_names}")
                stage_results = await asyncio.gather(*tasks, return_exceptions=True)

                for agent_name, result in zip(agent_names, stage_results):
                    agents_used.append(agent_name)
                    
                    if isinstance(result, Exception):
                        logger.error(f"Agent {agent_name} failed execution: {result}")
                        timeline.append({
                            "agent": agent_name,
                            "execution_time_ms": 0,
                            "status": "failure",
                            "message": str(result),
                            "confidence": 0.0
                        })
                    else:
                        agent_responses.append(result["response"])
                        timeline.append({
                            "agent": agent_name,
                            "execution_time_ms": result["latency_ms"],
                            "status": "success",
                            "confidence": result["response"].get("confidence", 0.0),
                            "answer": result["response"].get("answer", "")
                        })

        # 6. Run Response Synthesizer if requested
        synth_res = {}
        if synthesize_final_answer:
            logger.info("Running ResponseSynthesizer...")
            synth_start = time.time()
            try:
                synth_res = await self.synthesizer.synthesize(
                    query=query,
                    agent_responses=agent_responses,
                    memory_context=memory_context,
                    search_results=search_results,
                    tool_outputs=tool_outputs
                )
                synth_latency = time.time() - synth_start
                logger.info(f"ResponseSynthesizer completed in {synth_latency:.2f}s")
                timeline.append({
                    "agent": "ResponseSynthesizer",
                    "execution_time_ms": int(synth_latency * 1000),
                    "status": "success"
                })
            except Exception as e:
                synth_latency = time.time() - synth_start
                logger.error(f"ResponseSynthesizer failed: {e}")
                timeline.append({
                    "agent": "ResponseSynthesizer",
                    "execution_time_ms": int(synth_latency * 1000),
                    "status": "failure",
                    "message": str(e)
                })
                # Fallback synthesis
                fallback_answer = "\n\n".join([f"### {r.get('agent')}\n{r.get('answer')}" for r in agent_responses])
                synth_res = {
                    "summary": "Fallback summary compiled from individual agents.",
                    "detailed_explanation": fallback_answer,
                    "agent_contributions": [f"{r.get('agent')} (direct contribution)" for r in agent_responses],
                    "confidence_score": 0.5
                }
        else:
            # Synthesis bypassed, compile direct report from tools/search
            logger.info("Bypassing ResponseSynthesizer per Planner decision")
            direct_parts = []
            if tool_outputs:
                direct_parts.append("### Direct Tool Outputs")
                for t_name, val in tool_outputs.items():
                    direct_parts.append(f"**{t_name}**:\n```json\n{json.dumps(val, indent=2)}\n```")
            if search_results:
                direct_parts.append("### Codebase Search Results")
                for r in search_results:
                    direct_parts.append(f"- **{r['metadata'].get('path', 'unknown')}** (similarity={r['similarity']:.2f}):\n{r['content']}")
            
            detailed_explanation = "\n\n".join(direct_parts) if direct_parts else "No tools or search results were requested, and LLM synthesis was bypassed."
            synth_res = {
                "summary": "Direct result compiled from tools/search.",
                "detailed_explanation": detailed_explanation,
                "agent_contributions": ["Direct tool output execution."],
                "confidence_score": 1.0
            }
            timeline.append({
                "agent": "ResponseSynthesizer",
                "execution_time_ms": 0,
                "status": "success",
                "message": "Bypassed synthesizer"
            })

        total_time_ms = int((time.time() - start_total) * 1000)

        # Merge citations from all agent responses and search results
        references = []
        for r in agent_responses:
            references.extend(r.get("citations", []))
        for r in search_results:
            path = r["metadata"].get("path")
            if path and path not in references:
                references.append(path)

        unique_references = []
        for ref in references:
            if ref not in unique_references:
                unique_references.append(ref)

        answer = synth_res.get("detailed_explanation", "") or ""
        if not answer:
            logger.warning("Synthesized response was empty. Falling back to agent answers or summary.")
            if agent_responses:
                fallback_answer = "\n\n".join(
                    f"### {r.get('agent', 'UnnamedAgent')}\n{r.get('answer', '') or 'No answer generated.'}"
                    for r in agent_responses
                ).strip()
                answer = fallback_answer or synth_res.get("summary", "")
            else:
                answer = synth_res.get("summary", "No answer could be generated from the agents.")

        return {
            "answer": answer,
            "summary": synth_res.get("summary", ""),
            "agents_used": agents_used,
            "confidence": synth_res.get("confidence_score", 0.0),
            "references": unique_references,
            "agent_contributions": synth_res.get("agent_contributions", []),
            "planner_decision": planner_res,
            "timeline": timeline,
            "total_time_ms": total_time_ms,
            "retrieved_context": search_results
        }

    async def _run_agent_with_retry(
        self,
        agent_name: str,
        profile: Dict[str, Any],
        graph: Dict[str, Any],
        summary: Dict[str, Any],
        report: str,
        query: str,
        retries: int = 2
    ) -> Dict[str, Any]:
        agent = self.agents[agent_name]
        
        for attempt in range(retries + 1):
            start = time.time()
            try:
                response = await agent.run(profile, graph, summary, report, query)
                latency_ms = int((time.time() - start) * 1000)
                return {
                    "response": response,
                    "latency_ms": latency_ms
                }
            except Exception as e:
                logger.warning(f"Agent {agent_name} attempt {attempt + 1} failed: {e}")
                if attempt == retries:
                    raise e
                await asyncio.sleep(0.5)
