import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, get_args, get_origin

from pydantic import TypeAdapter
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BASE_DIR.parent
ROOT_ENV_FILE = PROJECT_ROOT / ".env"
SECONDARY_ENV_FILE = BASE_DIR / ".env"
MODEL_REGISTRY_FILE = BASE_DIR / "config" / "models.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(PROJECT_ROOT / ".env"), str(BASE_DIR / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    dashscope_api_key: str = ""
    model_registry_path: str = "config/models.json"

    md5_file_path: str = "storage/md5/md5.txt"
    chat_history_directory: str = "storage/chat_history"

    collection_name: str = "rag"
    persist_directory: str = "storage/chroma_db"

    chunk_size: int = 1000
    chunk_overlap: int = 100
    separators: list[str] = ["\n\n", "\n", ".", "!", "?", "。", "！", "？", " ", ""]
    max_spliter_char_num: int = 1000

    similarity_threshold: int | None = None
    retrieve_top_k: int = 10
    rerank_enabled: bool = True
    rerank_model_name: str = "qwen3-vl-rerank"
    rerank_top_n: int = 5
    rerank_min_docs: int = 2
    retrieval_neighbor_chunks: int = 2
    rerank_fallback_to_retrieval: bool = True
    rerank_api_timeout_seconds: float = 10.0

    embedding_model_name: str = "text-embedding-v2"
    chat_model_name: str = "qwen3-max"
    rewrite_enabled: bool = True
    rewrite_model_name: str = ""
    rewrite_history_turns: int = 3
    rewrite_max_query_length: int = 200
    rewrite_fallback_to_original: bool = True
    rewrite_min_reranked_docs: int = 3
    rewrite_quality_top1_threshold: float = 0.7
    rewrite_quality_top3_avg_threshold: float = 0.55
    rewrite_low_top1_threshold: float = 0.45
    rewrite_low_top3_avg_threshold: float = 0.35
    rewrite_compare_margin: float = 0.08


CONFIG_FIELD_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "key": "model_registry_json",
        "label": "模型注册表",
        "description": "为 chat、rewrite、embedding、rerank 指定模型、provider、base_url 和 api_key。",
        "group": "模型配置",
        "input_type": "json-object",
        "advanced": False,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "dashscope_api_key",
        "label": "API Key",
        "description": "DashScope 百炼平台的访问密钥。",
        "group": "常用配置",
        "input_type": "password",
        "advanced": False,
        "sensitive": True,
        "nullable": False,
    },
    {
        "key": "chat_model_name",
        "label": "对话模型",
        "description": "主对话链路使用的模型名称。",
        "group": "常用配置",
        "input_type": "text",
        "advanced": False,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "embedding_model_name",
        "label": "向量模型",
        "description": "文档向量化和检索使用的 embedding 模型。",
        "group": "常用配置",
        "input_type": "text",
        "advanced": False,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "rerank_model_name",
        "label": "重排模型",
        "description": "检索结果重排时使用的模型名称。",
        "group": "常用配置",
        "input_type": "text",
        "advanced": False,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "retrieve_top_k",
        "label": "检索 Top K",
        "description": "初始向量检索返回的文档数量。",
        "group": "常用配置",
        "input_type": "number",
        "advanced": False,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "rerank_enabled",
        "label": "启用重排",
        "description": "是否对检索结果进行 rerank。",
        "group": "常用配置",
        "input_type": "checkbox",
        "advanced": False,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "rewrite_enabled",
        "label": "启用 Query Rewrite",
        "description": "是否在召回质量不足时改写用户问题。",
        "group": "常用配置",
        "input_type": "checkbox",
        "advanced": False,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "md5_file_path",
        "label": "MD5 文件路径",
        "description": "去重摘要文件的保存路径。",
        "group": "存储路径",
        "input_type": "text",
        "advanced": True,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "chat_history_directory",
        "label": "会话历史目录",
        "description": "聊天记录 JSON 的保存目录。",
        "group": "存储路径",
        "input_type": "text",
        "advanced": True,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "collection_name",
        "label": "集合名称",
        "description": "Chroma collection 名称。",
        "group": "存储路径",
        "input_type": "text",
        "advanced": True,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "persist_directory",
        "label": "向量库存储目录",
        "description": "Chroma 持久化目录。",
        "group": "存储路径",
        "input_type": "text",
        "advanced": True,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "chunk_size",
        "label": "切片大小",
        "description": "文本切分时每个 chunk 的目标长度。",
        "group": "文本切分",
        "input_type": "number",
        "advanced": True,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "chunk_overlap",
        "label": "切片重叠长度",
        "description": "相邻 chunk 之间的重叠字符数。",
        "group": "文本切分",
        "input_type": "number",
        "advanced": True,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "separators",
        "label": "分隔符列表",
        "description": "文本切分优先使用的分隔符，使用 JSON 数组编辑。",
        "group": "文本切分",
        "input_type": "json-textarea",
        "advanced": True,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "max_spliter_char_num",
        "label": "切分阈值",
        "description": "大于该长度时才启用文本切分。",
        "group": "文本切分",
        "input_type": "number",
        "advanced": True,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "similarity_threshold",
        "label": "兼容阈值字段",
        "description": "兼容旧逻辑的阈值字段，设置后会覆盖 retrieve_top_k。",
        "group": "检索与重排",
        "input_type": "number",
        "advanced": True,
        "sensitive": False,
        "nullable": True,
    },
    {
        "key": "rerank_top_n",
        "label": "重排保留数量",
        "description": "重排后保留的文档数。",
        "group": "检索与重排",
        "input_type": "number",
        "advanced": True,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "rerank_min_docs",
        "label": "重排最小文档数",
        "description": "文档数量低于该值时回退到原始检索。",
        "group": "检索与重排",
        "input_type": "number",
        "advanced": True,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "retrieval_neighbor_chunks",
        "label": "邻接切片数",
        "description": "上下文扩展时补充的相邻 chunk 数量。",
        "group": "检索与重排",
        "input_type": "number",
        "advanced": True,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "rerank_fallback_to_retrieval",
        "label": "重排失败回退",
        "description": "重排失败时是否回退到原始检索结果。",
        "group": "检索与重排",
        "input_type": "checkbox",
        "advanced": True,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "rerank_api_timeout_seconds",
        "label": "重排超时秒数",
        "description": "调用 rerank API 的超时时间。",
        "group": "检索与重排",
        "input_type": "number",
        "advanced": True,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "rewrite_model_name",
        "label": "改写模型",
        "description": "问题改写所使用的模型，为空时复用对话模型。",
        "group": "问题改写",
        "input_type": "text",
        "advanced": True,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "rewrite_history_turns",
        "label": "改写历史轮数",
        "description": "参与问题改写的历史消息轮数。",
        "group": "问题改写",
        "input_type": "number",
        "advanced": True,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "rewrite_max_query_length",
        "label": "改写最大长度",
        "description": "问题改写输入允许的最大长度。",
        "group": "问题改写",
        "input_type": "number",
        "advanced": True,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "rewrite_fallback_to_original",
        "label": "改写失败回退原问题",
        "description": "改写失败时是否使用原始问题继续检索。",
        "group": "问题改写",
        "input_type": "checkbox",
        "advanced": True,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "rewrite_min_reranked_docs",
        "label": "改写最小文档数",
        "description": "低于该数量时更倾向触发改写。",
        "group": "问题改写",
        "input_type": "number",
        "advanced": True,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "rewrite_quality_top1_threshold",
        "label": "Top1 高质量阈值",
        "description": "top1 分数达到该阈值视为高质量召回。",
        "group": "问题改写",
        "input_type": "number",
        "advanced": True,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "rewrite_quality_top3_avg_threshold",
        "label": "Top3 平均高质量阈值",
        "description": "top3 平均分达到该阈值视为高质量召回。",
        "group": "问题改写",
        "input_type": "number",
        "advanced": True,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "rewrite_low_top1_threshold",
        "label": "Top1 低质量阈值",
        "description": "top1 分数低于该值时视为低质量召回。",
        "group": "问题改写",
        "input_type": "number",
        "advanced": True,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "rewrite_low_top3_avg_threshold",
        "label": "Top3 平均低质量阈值",
        "description": "top3 平均分低于该值时视为低质量召回。",
        "group": "问题改写",
        "input_type": "number",
        "advanced": True,
        "sensitive": False,
        "nullable": False,
    },
    {
        "key": "rewrite_compare_margin",
        "label": "改写比较边际",
        "description": "原问题与改写问题评分差的最小边际。",
        "group": "问题改写",
        "input_type": "number",
        "advanced": True,
        "sensitive": False,
        "nullable": False,
    },
)

CONFIG_FIELD_MAP = {item["key"]: item for item in CONFIG_FIELD_DEFINITIONS}
ENV_LINE_PATTERN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$")
SPECIAL_CONFIG_FIELDS = {"model_registry_json"}


def _settings_env_files() -> tuple[str, str]:
    return (str(ROOT_ENV_FILE), str(SECONDARY_ENV_FILE))


def _is_optional(annotation: Any) -> bool:
    origin = get_origin(annotation)
    if origin is None:
        return False
    return type(None) in get_args(annotation)


def _env_var_name(field_name: str) -> str:
    return field_name.upper()


def _serialize_env_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def validate_setting_updates(raw_updates: dict[str, Any]) -> dict[str, Any]:
    validated: dict[str, Any] = {}
    settings_fields = Settings.model_fields

    for key, value in raw_updates.items():
        if key in SPECIAL_CONFIG_FIELDS:
            if key == "model_registry_json":
                if not isinstance(value, dict):
                    raise ValueError("模型注册表必须是 JSON 对象")
                from app.core.model_registry import validate_model_registry_data

                validated[key] = validate_model_registry_data(value)
                continue

        field_info = settings_fields.get(key)
        if field_info is None or key not in CONFIG_FIELD_MAP:
            raise ValueError(f"不支持的配置项: {key}")

        if value is None:
            if not _is_optional(field_info.annotation):
                raise ValueError(f"配置项 {key} 不能为空")
            validated[key] = None
            continue

        validated[key] = TypeAdapter(field_info.annotation).validate_python(value)

    return validated


def upsert_settings(updates: dict[str, Any], *, env_path: Path | None = None) -> None:
    target_path = env_path or ROOT_ENV_FILE
    target_path.parent.mkdir(parents=True, exist_ok=True)
    registry_payload = updates.get("model_registry_json")
    if registry_payload is not None:
        from app.core.model_registry import clear_model_registry_cache, write_model_registry

        registry_path = _resolve_model_registry_path(
            updates.get("model_registry_path"),
        )
        write_model_registry(registry_payload, registry_path=registry_path)
        clear_model_registry_cache()

    existing_lines = (
        target_path.read_text(encoding="utf-8").splitlines()
        if target_path.exists()
        else []
    )

    env_updates = {
        _env_var_name(key): value
        for key, value in updates.items()
        if key not in SPECIAL_CONFIG_FIELDS
    }
    remaining = dict(env_updates)
    next_lines: list[str] = []

    for line in existing_lines:
        match = ENV_LINE_PATTERN.match(line)
        if not match:
            next_lines.append(line)
            continue

        env_key = match.group(1)
        if env_key not in remaining:
            next_lines.append(line)
            continue

        value = remaining.pop(env_key)
        if value is None:
            continue

        next_lines.append(f"{env_key}={_serialize_env_value(value)}")

    for env_key, value in remaining.items():
        if value is None:
            continue
        next_lines.append(f"{env_key}={_serialize_env_value(value)}")

    target_path.write_text("\n".join(next_lines).rstrip() + "\n", encoding="utf-8")

    for key, value in updates.items():
        if key in SPECIAL_CONFIG_FIELDS:
            continue
        env_key = _env_var_name(key)
        if value is None:
            os.environ.pop(env_key, None)
        else:
            os.environ[env_key] = _serialize_env_value(value)

    get_settings.cache_clear()


def build_config_fields() -> list[dict[str, Any]]:
    settings = get_settings()
    values = settings.model_dump()
    from app.core.model_registry import get_model_registry_payload

    values["model_registry_json"] = get_model_registry_payload(
        registry_path=_resolve_model_registry_path(settings.model_registry_path),
        settings=settings,
    )

    return [
        {
            **definition,
            "value": values[definition["key"]],
        }
        for definition in CONFIG_FIELD_DEFINITIONS
    ]


def _resolve_model_registry_path(path_value: str | None) -> Path:
    raw_path = Path(path_value or MODEL_REGISTRY_FILE)
    if raw_path.is_absolute():
        return raw_path
    return (BASE_DIR / raw_path).resolve()


@lru_cache
def get_settings() -> Settings:
    settings = Settings(_env_file=_settings_env_files())
    if settings.dashscope_api_key:
        os.environ["DASHSCOPE_API_KEY"] = settings.dashscope_api_key
    if settings.similarity_threshold is not None:
        settings.retrieve_top_k = settings.similarity_threshold
    for path_field in (
        "md5_file_path",
        "chat_history_directory",
        "persist_directory",
        "model_registry_path",
    ):
        field_value = Path(getattr(settings, path_field))
        if not field_value.is_absolute():
            base_path = BASE_DIR if path_field == "model_registry_path" else PROJECT_ROOT
            setattr(settings, path_field, str((base_path / field_value).resolve()))
    return settings
