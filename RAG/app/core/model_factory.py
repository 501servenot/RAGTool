import json
import os
from typing import Any
from urllib import request

from dashscope import TextReRank

from app.core.model_registry import ResolvedModelConfig


class DashScopeRerankClient:
    @staticmethod
    def call(**kwargs):
        return TextReRank.call(**kwargs)


class OpenAICompatibleRerankClient:
    def __init__(self, *, base_url: str, api_key: str | None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def call(
        self,
        *,
        model: str,
        query: str,
        documents: list[str],
        top_n: int,
        return_documents: bool = False,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "model": model,
            "query": query,
            "documents": documents,
            "top_n": top_n,
            "return_documents": return_documents,
        }
        target_url = f"{self.base_url}/rerank"
        headers = {"Content-Type": "application/json"}
        token = api_key or self.api_key
        if token:
            headers["Authorization"] = f"Bearer {token}"

        req = request.Request(
            target_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        with request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)


def create_chat_model(config: ResolvedModelConfig):
    provider = config.provider
    if provider.kind == "dashscope":
        if provider.api_key:
            os.environ["DASHSCOPE_API_KEY"] = provider.api_key
        from langchain_community.chat_models.tongyi import ChatTongyi

        return ChatTongyi(model=config.model)

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=config.model,
        api_key=provider.api_key,
        base_url=provider.base_url,
    )


def create_embedding_model(config: ResolvedModelConfig):
    provider = config.provider
    if provider.kind == "dashscope":
        if provider.api_key:
            os.environ["DASHSCOPE_API_KEY"] = provider.api_key
        from langchain_community.embeddings.dashscope import DashScopeEmbeddings

        return DashScopeEmbeddings(model=config.model)

    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(
        model=config.model,
        api_key=provider.api_key,
        base_url=provider.base_url,
    )


def create_rerank_client(config: ResolvedModelConfig):
    provider = config.provider
    if provider.kind == "dashscope":
        if provider.api_key:
            os.environ["DASHSCOPE_API_KEY"] = provider.api_key
        return DashScopeRerankClient()

    if not provider.base_url:
        raise ValueError("OpenAI 兼容 rerank provider 必须配置 base_url")
    return OpenAICompatibleRerankClient(
        base_url=provider.base_url,
        api_key=provider.api_key,
    )
