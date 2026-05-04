from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar


@dataclass
class Session:
    channel_id: int
    command: str
    history: list[dict] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    active: bool = True
    pending_content: str = ""
    pending_path: str = ""
    pending_note_id: str = ""
    pending_inbox_path: str = ""
    topic: str = ""
    web_results: list[dict] = field(default_factory=list)
    related_note_ids: list[str] = field(default_factory=list)
    raw_content: str = ""


class SessionManager:
    _sessions: ClassVar[dict[int, Session]] = {}

    @classmethod
    def create(cls, channel_id: int, command: str) -> Session:
        session = Session(channel_id=channel_id, command=command)
        cls._sessions[channel_id] = session
        return session

    @classmethod
    def get(cls, channel_id: int) -> Session | None:
        s = cls._sessions.get(channel_id)
        if s and s.active:
            return s
        return None

    @classmethod
    def close(cls, channel_id: int) -> None:
        if channel_id in cls._sessions:
            cls._sessions[channel_id].active = False
            del cls._sessions[channel_id]
