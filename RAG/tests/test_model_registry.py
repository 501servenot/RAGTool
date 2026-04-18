import importlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from app.core import config as config_module


class ModelRegistryModuleTest(unittest.TestCase):
    def test_model_registry_module_exists_and_resolves_env_placeholders(self):
        spec = importlib.util.find_spec("app.core.model_registry")
        self.assertIsNotNone(spec)

        module = importlib.import_module("app.core.model_registry")

        with tempfile.TemporaryDirectory() as tempdir:
            registry_path = Path(tempdir) / "models.json"
            registry_path.write_text(
                json.dumps(
                    {
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
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-openai-test"}, clear=False):
                registry = module.load_model_registry(registry_path=registry_path)

            chat_config = registry.get_assignment("chat")
            self.assertEqual(chat_config.model, "gpt-4o-mini")
            self.assertEqual(chat_config.provider.base_url, "https://api.openai.com/v1")
            self.assertEqual(chat_config.provider.api_key, "sk-openai-test")

    def test_load_model_registry_falls_back_to_legacy_settings(self):
        spec = importlib.util.find_spec("app.core.model_registry")
        self.assertIsNotNone(spec)

        module = importlib.import_module("app.core.model_registry")

        with tempfile.TemporaryDirectory() as tempdir:
            env_path = Path(tempdir) / ".env"
            env_path.write_text(
                "DASHSCOPE_API_KEY=sk-dashscope\n"
                "CHAT_MODEL_NAME=qwen-chat\n"
                "EMBEDDING_MODEL_NAME=text-embedding-v2\n"
                "RERANK_MODEL_NAME=qwen-rerank\n",
                encoding="utf-8",
            )

            with patch.object(config_module, "ROOT_ENV_FILE", env_path):
                settings = config_module.Settings(_env_file=(str(env_path), str(env_path)))
                registry = module.load_model_registry(
                    registry_path=Path(tempdir) / "missing-models.json",
                    settings=settings,
                )

            self.assertEqual(registry.assignments.chat, "legacy_chat")
            self.assertEqual(registry.assignments.embedding, "legacy_embedding")
            self.assertEqual(registry.assignments.rerank, "legacy_rerank")
            self.assertEqual(registry.models["legacy_chat"].model, "qwen-chat")


if __name__ == "__main__":
    unittest.main()
