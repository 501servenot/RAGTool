import json
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage, message_to_dict


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from app.api.v1.endpoints.chat import router
from app.services.chat_history import ChatHistoryService


def write_history_file(directory: Path, session_id: str, messages: list) -> Path:
    path = directory / f"{session_id}.json"
    serialized = [message_to_dict(message) for message in messages]
    path.write_text(json.dumps(serialized, ensure_ascii=False), encoding="utf-8")
    return path


class ChatHistoryServiceTest(unittest.TestCase):
    def test_list_sessions_returns_latest_first_with_generated_title(self):
        with tempfile.TemporaryDirectory() as tempdir:
            history_dir = Path(tempdir)
            older = write_history_file(
                history_dir,
                "session-older",
                [
                    HumanMessage(content="这是一个很长很长的第一条用户消息，用来生成标题并且需要截断"),
                    AIMessage(content="第一条回答"),
                ],
            )
            newer = write_history_file(
                history_dir,
                "session-newer",
                [
                    HumanMessage(content="最近一次会话"),
                    AIMessage(content="最近一次回答"),
                ],
            )
            older.touch()
            newer.touch()

            service = ChatHistoryService(storage_path=str(history_dir))

            sessions = service.list_sessions()

            self.assertEqual([item.session_id for item in sessions], ["session-newer", "session-older"])
            self.assertEqual(sessions[0].title, "最近一次会话")
            self.assertTrue(sessions[1].title.startswith("这是一个很长很长的第一条用户消息"))

    def test_list_sessions_skips_invalid_history_files(self):
        with tempfile.TemporaryDirectory() as tempdir:
            history_dir = Path(tempdir)
            write_history_file(
                history_dir,
                "session-valid",
                [
                    HumanMessage(content="有效会话"),
                    AIMessage(content="有效回答"),
                ],
            )
            (history_dir / "session-broken.json").write_text("{broken json", encoding="utf-8")
            service = ChatHistoryService(storage_path=str(history_dir))

            sessions = service.list_sessions()

            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0].session_id, "session-valid")

    def test_get_session_messages_maps_roles_and_content(self):
        with tempfile.TemporaryDirectory() as tempdir:
            history_dir = Path(tempdir)
            write_history_file(
                history_dir,
                "session-1",
                [
                    HumanMessage(content="你好"),
                    AIMessage(content="你好，我可以帮你什么？"),
                ],
            )
            service = ChatHistoryService(storage_path=str(history_dir))

            messages = service.get_session_messages("session-1")

            self.assertEqual(len(messages), 2)
            self.assertEqual(messages[0].role, "user")
            self.assertEqual(messages[0].content, "你好")
            self.assertEqual(messages[1].role, "ai")
            self.assertEqual(messages[1].content, "你好，我可以帮你什么？")

    def test_delete_session_removes_history_file(self):
        with tempfile.TemporaryDirectory() as tempdir:
            history_dir = Path(tempdir)
            file_path = write_history_file(
                history_dir,
                "session-delete-me",
                [
                    HumanMessage(content="删除我"),
                    AIMessage(content="好的"),
                ],
            )
            service = ChatHistoryService(storage_path=str(history_dir))

            deleted = service.delete_session("session-delete-me")

            self.assertEqual(deleted.session_id, "session-delete-me")
            self.assertFalse(file_path.exists())


class ChatHistoryEndpointTest(unittest.TestCase):
    def test_get_sessions_and_messages_routes(self):
        with tempfile.TemporaryDirectory() as tempdir:
            history_dir = Path(tempdir)
            write_history_file(
                history_dir,
                "session-1",
                [
                    HumanMessage(content="帮我总结上传功能"),
                    AIMessage(content="上传功能支持 txt、md、pdf"),
                ],
            )
            app = FastAPI()
            app.state.rag_service = object()
            app.state.chat_history_service = ChatHistoryService(storage_path=str(history_dir))
            app.include_router(router, prefix="/api/v1")
            client = TestClient(app)

            sessions_response = client.get("/api/v1/chat/sessions")
            messages_response = client.get("/api/v1/chat/sessions/session-1/messages")

            self.assertEqual(sessions_response.status_code, 200)
            self.assertEqual(messages_response.status_code, 200)
            self.assertEqual(sessions_response.json()[0]["session_id"], "session-1")
            self.assertEqual(messages_response.json()[0]["role"], "user")

    def test_delete_session_route(self):
        with tempfile.TemporaryDirectory() as tempdir:
            history_dir = Path(tempdir)
            write_history_file(
                history_dir,
                "session-delete",
                [
                    HumanMessage(content="待删除"),
                    AIMessage(content="好的"),
                ],
            )
            app = FastAPI()
            app.state.rag_service = object()
            app.state.chat_history_service = ChatHistoryService(storage_path=str(history_dir))
            app.include_router(router, prefix="/api/v1")
            client = TestClient(app)

            delete_response = client.delete("/api/v1/chat/sessions/session-delete")
            missing_response = client.delete("/api/v1/chat/sessions/not-exist")

            self.assertEqual(delete_response.status_code, 200)
            self.assertEqual(delete_response.json()["session_id"], "session-delete")
            self.assertEqual(missing_response.status_code, 404)

