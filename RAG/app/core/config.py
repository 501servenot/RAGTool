import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BASE_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(PROJECT_ROOT / ".env"), str(BASE_DIR / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    dashscope_api_key: str = ""

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


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.dashscope_api_key:
        os.environ["DASHSCOPE_API_KEY"] = settings.dashscope_api_key
    if settings.similarity_threshold is not None:
        settings.retrieve_top_k = settings.similarity_threshold
    for path_field in (
        "md5_file_path",
        "chat_history_directory",
        "persist_directory",
    ):
        field_value = Path(getattr(settings, path_field))
        if not field_value.is_absolute():
            setattr(settings, path_field, str((PROJECT_ROOT / field_value).resolve()))
    return settings
