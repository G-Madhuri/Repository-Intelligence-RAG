import os
import json
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from memory.conversation_manager import conversation_manager, ConversationSession, MessageRecord

logger = logging.getLogger("session_manager")

class SessionManager:
    """
    Manages persistence and high-level metadata for multiple repository sessions.
    Saves and loads conversation history and repository state to/from disk.
    """
    def __init__(self, storage_dir: str = None):
        if storage_dir is None:
            storage_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage")
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        self.conversations_file = os.path.join(self.storage_dir, "conversations.json")
        self.load_all()

    def load_all(self):
        if os.path.exists(self.conversations_file):
            try:
                with open(self.conversations_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for session_id, s_data in data.items():
                        session = ConversationSession(
                            session_id=session_id,
                            repo_id=s_data.get("repo_id"),
                            summary=s_data.get("summary", ""),
                            history=[
                                MessageRecord(**msg) for msg in s_data.get("history", [])
                            ]
                        )
                        conversation_manager._sessions[session_id] = session
                logger.info(f"Loaded conversations from {self.conversations_file}")
            except Exception as e:
                logger.error(f"Error loading conversations: {e}")

    def save_all(self):
        data = {}
        for session_id, session in conversation_manager._sessions.items():
            data[session_id] = {
                "session_id": session.session_id,
                "repo_id": session.repo_id,
                "summary": session.summary,
                "history": [msg.model_dump() for msg in session.history]
            }
        try:
            with open(self.conversations_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved conversations to {self.conversations_file}")
        except Exception as e:
            logger.error(f"Error saving conversations: {e}")

    def get_session_history(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        session = conversation_manager.get_session(session_id)
        if not session:
            return None
        return [msg.model_dump() for msg in session.history]

# Global session manager singleton
session_manager = SessionManager()
