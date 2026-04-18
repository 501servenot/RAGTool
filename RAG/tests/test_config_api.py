import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from app.api.v1.endpoints.config import router
from app.core import config as config_module


class ConfigStoreTest(unittest.TestCase):
    def test_upsert_settings_writes_serialized_values_and_removes_none(self):
        with tempfile.TemporaryDirectory() as tempdir:
            env_path = Path(tempdir) / ".env"
            env_path.write_text(
                "CHAT_MODEL_NAME=old-model\n"
                "SIMILARITY_THRESHOLD=9\n"
                "KEEP_ME=1\n",
                encoding="utf-8",
            )

            with patch.object(config_module, "ROOT_ENV_FILE", env_path):
                config_module.upsert_settings(
                    {
                        "chat_model_name": "qwen-plus",
                        "rerank_enabled": False,
                        "separators": ["\n", "。"],
                        "similarity_threshold": None,
                    }
                )

            content = env_path.read_text(encoding="utf-8")
            self.assertIn("CHAT_MODEL_NAME=qwen-plus", content)
            self.assertIn("RERANK_ENABLED=false", content)
            self.assertIn('SEPARATORS=["\\n", "。"]', content)
            self.assertNotIn("SIMILARITY_THRESHOLD=", content)
            self.assertIn("KEEP_ME=1", content)


class ConfigEndpointTest(unittest.TestCase):
    def test_get_and_patch_config_routes(self):
        with tempfile.TemporaryDirectory() as tempdir:
            env_path = Path(tempdir) / ".env"
            registry_path = Path(tempdir) / "models.json"
            registry_path.write_text(
                '{"providers":{"dashscope":{"kind":"dashscope","api_key":"${DASHSCOPE_API_KEY}"}},"models":{"chat_default":{"provider":"dashscope","type":"chat","model":"qwen3-max"}},"assignments":{"chat":"chat_default","rewrite":"chat_default","embedding":"chat_default","rerank":"chat_default"}}',
                encoding="utf-8",
            )
            env_path.write_text(
                "DASHSCOPE_API_KEY=sk-test\n"
                "CHAT_MODEL_NAME=qwen3-max\n"
                "RETRIEVE_TOP_K=10\n",
                encoding="utf-8",
            )

            app = FastAPI()
            app.state.kb_service = object()
            app.state.rag_service = object()
            app.state.chat_history_service = object()
            app.include_router(router, prefix="/api/v1")

            reload_calls: list[tuple[object, object, object]] = []

            def fake_reload(target_app: FastAPI) -> None:
                reload_calls.append(
                    (
                        target_app.state.kb_service,
                        target_app.state.rag_service,
                        target_app.state.chat_history_service,
                    )
                )
                target_app.state.kb_service = "kb-reloaded"
                target_app.state.rag_service = "rag-reloaded"
                target_app.state.chat_history_service = "history-reloaded"

            with patch.object(config_module, "ROOT_ENV_FILE", env_path), patch.object(
                config_module,
                "MODEL_REGISTRY_FILE",
                registry_path,
            ), patch(
                "app.api.v1.endpoints.config.reload_runtime_services",
                side_effect=fake_reload,
            ):
                client = TestClient(app)

                get_response = client.get("/api/v1/config")
                patch_response = client.patch(
                    "/api/v1/config",
                    json={
                        "values": {
                            "chat_model_name": "qwen3-plus",
                            "retrieve_top_k": 6,
                            "dashscope_api_key": "sk-updated",
                            "model_registry_json": {
                                "providers": {
                                    "openai_official": {
                                        "kind": "openai_compatible",
                                        "base_url": "https://api.openai.com/v1",
                                        "api_key": "${OPENAI_API_KEY}",
                                    }
                                },
                                "models": {
                                    "chat_default": {
                                        "provider": "openai_official",
                                        "type": "chat",
                                        "model": "gpt-4o-mini",
                                    }
                                },
                                "assignments": {
                                    "chat": "chat_default",
                                    "rewrite": "chat_default",
                                    "embedding": "chat_default",
                                    "rerank": "chat_default",
                                },
                            },
                        }
                    },
                )

            self.assertEqual(get_response.status_code, 200)
            fields = get_response.json()["fields"]
            self.assertTrue(any(field["key"] == "dashscope_api_key" for field in fields))
            self.assertTrue(any(field["key"] == "separators" for field in fields))
            self.assertTrue(any(field["key"] == "model_registry_json" for field in fields))

            self.assertEqual(patch_response.status_code, 200)
            body = patch_response.json()
            self.assertEqual(body["message"], "保存成功，配置已刷新")
            updated_field = next(
                field for field in body["fields"] if field["key"] == "chat_model_name"
            )
            self.assertEqual(updated_field["value"], "qwen3-plus")
            self.assertEqual(len(reload_calls), 1)
            self.assertEqual(app.state.kb_service, "kb-reloaded")

            content = env_path.read_text(encoding="utf-8")
            self.assertIn("CHAT_MODEL_NAME=qwen3-plus", content)
            self.assertIn("RETRIEVE_TOP_K=6", content)
            self.assertIn("DASHSCOPE_API_KEY=sk-updated", content)
            registry_content = registry_path.read_text(encoding="utf-8")
            self.assertIn('"openai_official"', registry_content)
            self.assertIn('"gpt-4o-mini"', registry_content)


if __name__ == "__main__":
    unittest.main()
