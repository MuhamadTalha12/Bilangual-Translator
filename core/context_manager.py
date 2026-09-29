from collections import defaultdict
from typing import List, Dict

class ContextManager:
    """Manages ephemeral chat history for multi-turn context resolution."""
    def __init__(self, max_history: int = 5):
        self.sessions: Dict[str, List[Dict[str, str]]] = defaultdict(list)
        self.max_history = max_history

    def add_message(self, session_id: str, role: str, content: str) -> None:
        self.sessions[session_id].append({"role": role, "content": content})
        if len(self.sessions[session_id]) > self.max_history * 2:
            self.sessions[session_id].pop(0)

    def get_messages(self, session_id: str) -> List[Dict[str, str]]:
        return list(self.sessions.get(session_id, []))

    def clear_session(self, session_id: str) -> None:
        if session_id in self.sessions:
            del self.sessions[session_id]

    def get_history_string(self, session_id: str) -> str:
        history = self.sessions.get(session_id, [])
        if not history:
            return "No previous context."
        return "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in history])