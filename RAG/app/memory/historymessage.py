import json
import os
import re

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict


def _normalize_session_id(session_id: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]", "_", session_id).strip("._")
    return normalized or "default_session"


class FileChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, session_id: str, storage_path: str):
        self.session_id = session_id
        self.storage_path = storage_path

        os.makedirs(self.storage_path, exist_ok=True)
        filename = f"{_normalize_session_id(session_id)}.json"
        self.file_path = os.path.join(self.storage_path, filename)

    @property
    def messages(self) -> list[BaseMessage]:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                messages_data = json.load(f)
        except FileNotFoundError:
            return []

        return messages_from_dict(messages_data)

    def add_messages(self, messages: list[BaseMessage]) -> None:
        all_messages = list(self.messages)
        all_messages.extend(messages)

        serialized_messages = [message_to_dict(message) for message in all_messages]

        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(serialized_messages, f, ensure_ascii=False, indent=2)

    def clear(self) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False)
