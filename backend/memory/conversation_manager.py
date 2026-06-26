import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class MessageRecord(BaseModel):
    role: str  # 'user' | 'assistant'
    content: str
    timestamp: float = Field(default_factory=time.time)
    retrieved_context: Optional[List[Dict[str, Any]]] = None
    agent_decisions: Optional[Dict[str, Any]] = None

class ConversationSession(BaseModel):
    session_id: str
    repo_id: str
    history: List[MessageRecord] = Field(default_factory=list)
    summary: str = ""

class ConversationManager:
    """
    Manages multi-session conversation tracking, caching history in-memory.
    Persists context, questions, answers, and internal timeline decisions.
    """
    def __init__(self):
        self._sessions: Dict[str, ConversationSession] = {}

    def get_or_create_session(self, session_id: str, repo_id: str) -> ConversationSession:
        if session_id not in self._sessions:
            self._sessions[session_id] = ConversationSession(session_id=session_id, repo_id=repo_id)
        return self._sessions[session_id]

    def add_message(
        self,
        session_id: str,
        repo_id: str,
        role: str,
        content: str,
        retrieved_context: Optional[List[Dict[str, Any]]] = None,
        agent_decisions: Optional[Dict[str, Any]] = None
    ) -> MessageRecord:
        session = self.get_or_create_session(session_id, repo_id)
        record = MessageRecord(
            role=role,
            content=content,
            timestamp=time.time(),
            retrieved_context=retrieved_context,
            agent_decisions=agent_decisions
        )
        session.history.append(record)
        
        # Keep summary updated with the last user prompt summary or simple description
        if role == "user" and not session.summary:
            # First query acts as session title/summary
            session.summary = content[:40] + ("..." if len(content) > 40 else "")
            
        return record

    def update_summary(self, session_id: str, summary: str):
        if session_id in self._sessions:
            self._sessions[session_id].summary = summary

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        return self._sessions.get(session_id)

    def list_sessions_for_repo(self, repo_id: str) -> List[Dict[str, Any]]:
        return [
            {
                "session_id": s.session_id,
                "repo_id": s.repo_id,
                "summary": s.summary,
                "message_count": len(s.history),
                "last_updated": s.history[-1].timestamp if s.history else time.time()
            }
            for s in self._sessions.values() if s.repo_id == repo_id
        ]

    def clear_sessions(self):
        self._sessions.clear()

# Global conversation manager singleton
conversation_manager = ConversationManager()
