from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionData:
    """Data stored for a conversation session."""

    session_id: str
    created_at: float
    last_seen_at: float
    messages: list[dict[str, Any]] = field(default_factory=list)


class InMemorySessionStore:
    """Very small in-memory session store with TTL.

    Suitable only for single-instance dev deployments.
    """

    def __init__(self, ttl_seconds: int):
        self._ttl_seconds = ttl_seconds
        self._sessions: dict[str, SessionData] = {}

    def _now(self) -> float:
        return time.time()

    def _gc(self) -> None:
        now = self._now()
        expired = [sid for sid, s in self._sessions.items() if now - s.last_seen_at > self._ttl_seconds]
        for sid in expired:
            self._sessions.pop(sid, None)

    # PUBLIC_INTERFACE
    def get_or_create(self, session_id: str | None) -> SessionData:
        """Get an existing session or create a new one.

        Args:
            session_id: Existing session id if client provided one.

        Returns:
            SessionData: Session record.
        """
        self._gc()
        now = self._now()

        if session_id and session_id in self._sessions:
            s = self._sessions[session_id]
            s.last_seen_at = now
            return s

        new_id = session_id or str(uuid.uuid4())
        s = SessionData(session_id=new_id, created_at=now, last_seen_at=now)
        self._sessions[new_id] = s
        return s

    # PUBLIC_INTERFACE
    def append_message(self, session_id: str, role: str, content: str, extra: dict[str, Any] | None = None) -> None:
        """Append a message to a session."""
        self._gc()
        s = self._sessions.get(session_id)
        if not s:
            s = self.get_or_create(session_id)
        s.last_seen_at = self._now()
        msg: dict[str, Any] = {"role": role, "content": content, "ts": s.last_seen_at}
        if extra:
            msg["extra"] = extra
        s.messages.append(msg)
