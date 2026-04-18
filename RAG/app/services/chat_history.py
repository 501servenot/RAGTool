import json
from datetime import datetime
from pathlib import Path

from app.core.config import get_settings
from app.memory.historymessage import FileChatMessageHistory, _normalize_session_id
from app.schemas.chat import (
    ChatHistoryMessage,
    ChatSessionSummary,
    DeleteChatSessionResponse,
)


class ChatHistoryService:
    def __init__(self, storage_path: str | None = None):
        settings = get_settings()
        self.storage_path = Path(storage_path or settings.chat_history_directory)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def list_sessions(self) -> list[ChatSessionSummary]:
        session_files = sorted(
            self.storage_path.glob("*.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        sessions: list[ChatSessionSummary] = []
        for path in session_files:
          try:
              sessions.append(self._build_session_summary(path))
          except (json.JSONDecodeError, TypeError, ValueError):
              continue
        return sessions

    def get_session_messages(self, session_id: str) -> list[ChatHistoryMessage]:
        return self._load_session_messages(session_id, skip_invalid=True)

    def delete_session(self, session_id: str) -> DeleteChatSessionResponse:
        file_path = self.storage_path / f"{_normalize_session_id(session_id)}.json"
        if not file_path.exists():
            raise FileNotFoundError(session_id)
        file_path.unlink()
        return DeleteChatSessionResponse(
            session_id=session_id,
            message="删除成功",
        )

    def _load_session_messages(
        self,
        session_id: str,
        *,
        skip_invalid: bool,
    ) -> list[ChatHistoryMessage]:
        history = FileChatMessageHistory(
            session_id=session_id,
            storage_path=str(self.storage_path),
        )
        try:
            raw_messages = history.messages
        except (json.JSONDecodeError, TypeError, ValueError):
            if skip_invalid:
                return []
            raise
        return [
            ChatHistoryMessage(
                role="user" if message.type == "human" else "ai",
                content=str(message.content),
            )
            for message in raw_messages
            if message.type in {"human", "ai"}
        ]

    def _build_session_summary(self, path: Path) -> ChatSessionSummary:
        session_id = path.stem
        messages = self._load_session_messages(session_id, skip_invalid=False)
        title = next(
            (self._truncate(message.content) for message in messages if message.role == "user"),
            "新会话",
        )
        updated_at = datetime.fromtimestamp(path.stat().st_mtime).isoformat()
        return ChatSessionSummary(
            session_id=session_id,
            title=title,
            updated_at=updated_at,
        )

    @staticmethod
    def _truncate(text: str, max_length: int = 24) -> str:
        if len(text) <= max_length:
            return text
        return f"{text[:max_length]}..."
