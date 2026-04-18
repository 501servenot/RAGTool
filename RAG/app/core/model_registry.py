import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


ENV_PLACEHOLDER_PATTERN = re.compile(r"^\$\{([A-Z0-9_]+)\}$")

ProviderKind = Literal["openai_compatible", "dashscope"]
ModelType = Literal["chat", "embedding", "rerank"]
AssignmentName = Literal["chat", "rewrite", "embedding", "rerank"]
MODEL_ASSIGNMENT_NAMES: tuple[AssignmentName, ...] = (
    "chat",
    "rewrite",
    "embedding",
    "rerank",
)


class ProviderConfig(BaseModel):
    kind: ProviderKind
    base_url: str | None = None
    api_key: str | None = None


class ModelConfig(BaseModel):
    provider: str
    type: ModelType
    model: str


class AssignmentConfig(BaseModel):
    chat: str
    rewrite: str | None = None
    embedding: str
    rerank: str

    @model_validator(mode="after")
    def fill_rewrite(self) -> "AssignmentConfig":
        if not self.rewrite:
            self.rewrite = self.chat
        return self


class ResolvedProviderConfig(BaseModel):
    name: str
    kind: ProviderKind
    base_url: str | None = None
    api_key: str | None = None


class ResolvedModelConfig(BaseModel):
    key: str
    type: ModelType
    model: str
    provider_name: str
    provider: ResolvedProviderConfig


class ModelRegistry(BaseModel):
    providers: dict[str, ProviderConfig]
    models: dict[str, ModelConfig]
    assignments: AssignmentConfig

    @model_validator(mode="after")
    def validate_references(self) -> "ModelRegistry":
        for model_name, model in self.models.items():
            if model.provider not in self.providers:
                raise ValueError(f"模型 {model_name} 引用了不存在的 provider: {model.provider}")

        for assignment_name in ("chat", "rewrite", "embedding", "rerank"):
            model_key = getattr(self.assignments, assignment_name)
            if model_key not in self.models:
                raise ValueError(
                    f"assignment {assignment_name} 引用了不存在的模型: {model_key}"
                )
        return self

    def get_assignment(self, assignment_name: AssignmentName) -> ResolvedModelConfig:
        model_key = getattr(self.assignments, assignment_name)
        model = self.models[model_key]
        provider = self.providers[model.provider]
        return ResolvedModelConfig(
            key=model_key,
            type=model.type,
            model=model.model,
            provider_name=model.provider,
            provider=ResolvedProviderConfig(
                name=model.provider,
                kind=provider.kind,
                base_url=_resolve_env_placeholder(provider.base_url),
                api_key=_resolve_env_placeholder(provider.api_key),
            ),
        )


def _resolve_env_placeholder(value: str | None) -> str | None:
    if value is None:
        return None
    matched = ENV_PLACEHOLDER_PATTERN.match(value.strip())
    if not matched:
        return value
    return os.getenv(matched.group(1), "")


def _read_registry_payload(registry_path: Path) -> dict[str, Any]:
    return json.loads(registry_path.read_text(encoding="utf-8"))


def build_legacy_registry_payload(settings) -> dict[str, Any]:
    dashscope_provider = {
        "kind": "dashscope",
        "api_key": "${DASHSCOPE_API_KEY}",
    }
    legacy_payload = {
        "providers": {
            "legacy_dashscope": dashscope_provider,
        },
        "models": {
            "legacy_chat": {
                "provider": "legacy_dashscope",
                "type": "chat",
                "model": settings.chat_model_name,
            },
            "legacy_rewrite": {
                "provider": "legacy_dashscope",
                "type": "chat",
                "model": settings.rewrite_model_name or settings.chat_model_name,
            },
            "legacy_embedding": {
                "provider": "legacy_dashscope",
                "type": "embedding",
                "model": settings.embedding_model_name,
            },
            "legacy_rerank": {
                "provider": "legacy_dashscope",
                "type": "rerank",
                "model": settings.rerank_model_name,
            },
        },
        "assignments": {
            "chat": "legacy_chat",
            "rewrite": "legacy_rewrite",
            "embedding": "legacy_embedding",
            "rerank": "legacy_rerank",
        },
    }
    return legacy_payload


def build_model_config_forms(payload: dict[str, Any]) -> dict[str, dict[str, str]]:
    registry = ModelRegistry.model_validate(payload)
    forms: dict[str, dict[str, str]] = {}

    for role in MODEL_ASSIGNMENT_NAMES:
        resolved = registry.get_assignment(role)
        forms[role] = {
            "provider_kind": resolved.provider.kind,
            "model": resolved.model,
            "base_url": resolved.provider.base_url or "",
            "api_key": resolved.provider.api_key or "",
        }

    return forms


def validate_model_config_forms(model_configs: dict[str, Any]) -> dict[str, dict[str, str]]:
    normalized: dict[str, dict[str, str]] = {}

    for role in MODEL_ASSIGNMENT_NAMES:
        role_config = model_configs.get(role)
        if not isinstance(role_config, dict):
            raise ValueError(f"{role} 模型配置不能为空")

        provider_kind = str(role_config.get("provider_kind", "")).strip()
        model_name = str(role_config.get("model", "")).strip()
        base_url = str(role_config.get("base_url", "")).strip()
        api_key = str(role_config.get("api_key", "")).strip()

        if provider_kind not in {"openai_compatible", "dashscope"}:
            raise ValueError(f"{role} 的 provider_kind 不合法")
        if not model_name:
            raise ValueError(f"{role} 的模型名称不能为空")
        if provider_kind == "openai_compatible" and not base_url:
            raise ValueError(f"{role} 使用 OpenAI 兼容接口时必须填写 URL")

        normalized[role] = {
            "provider_kind": provider_kind,
            "model": model_name,
            "base_url": base_url,
            "api_key": api_key,
        }

    return normalized


def build_registry_payload_from_forms(
    model_configs: dict[str, dict[str, str]],
) -> dict[str, Any]:
    providers: dict[str, dict[str, str]] = {}
    models: dict[str, dict[str, str]] = {}
    assignments: dict[str, str] = {}

    for role in MODEL_ASSIGNMENT_NAMES:
        role_config = model_configs[role]
        provider_name = f"{role}_provider"
        model_name = f"{role}_model"
        providers[provider_name] = {
            "kind": role_config["provider_kind"],
        }
        if role_config["base_url"]:
            providers[provider_name]["base_url"] = role_config["base_url"]
        if role_config["api_key"]:
            providers[provider_name]["api_key"] = role_config["api_key"]

        model_type = "chat" if role in {"chat", "rewrite"} else role
        models[model_name] = {
            "provider": provider_name,
            "type": model_type,
            "model": role_config["model"],
        }
        assignments[role] = model_name

    return validate_model_registry_data(
        {
            "providers": providers,
            "models": models,
            "assignments": assignments,
        }
    )


def validate_model_registry_data(payload: dict[str, Any]) -> dict[str, Any]:
    return ModelRegistry.model_validate(payload).model_dump(exclude_none=True)


def get_model_registry_payload(*, registry_path: Path, settings) -> dict[str, Any]:
    if registry_path.exists():
        return validate_model_registry_data(_read_registry_payload(registry_path))
    payload = build_legacy_registry_payload(settings)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def write_model_registry(payload: dict[str, Any], *, registry_path: Path) -> None:
    normalized = validate_model_registry_data(payload)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_model_registry(*, registry_path: Path, settings) -> ModelRegistry:
    payload = get_model_registry_payload(registry_path=registry_path, settings=settings)
    return ModelRegistry.model_validate(payload)


@lru_cache
def get_model_registry(*, registry_path: str) -> ModelRegistry:
    from app.core.config import get_settings

    settings = get_settings()
    return load_model_registry(registry_path=Path(registry_path), settings=settings)


def clear_model_registry_cache() -> None:
    get_model_registry.cache_clear()
