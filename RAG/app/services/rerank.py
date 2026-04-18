import asyncio
import logging
from typing import Any

from dashscope import TextReRank
from langchain_core.documents import Document

from app.core.config import get_settings


logger = logging.getLogger(__name__)


class RerankService:
    def __init__(
        self,
        client=None,
        *,
        model_name: str | None = None,
        top_n: int | None = None,
        timeout_seconds: float | None = None,
        fallback_to_retrieval: bool | None = None,
    ):
        settings = get_settings()
        self.client = client or TextReRank
        self.model_name = model_name or settings.rerank_model_name
        self.top_n = settings.rerank_top_n if top_n is None else top_n
        self.timeout_seconds = (
            settings.rerank_api_timeout_seconds
            if timeout_seconds is None
            else timeout_seconds
        )
        self.fallback_to_retrieval = (
            settings.rerank_fallback_to_retrieval
            if fallback_to_retrieval is None
            else fallback_to_retrieval
        )
        self.api_key = settings.dashscope_api_key or None

    async def rerank(self, query: str, docs: list[Document]) -> list[Document]:
        if not docs:
            return []

        documents = [doc.page_content for doc in docs]
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.call,
                    model=self.model_name,
                    query=query,
                    documents=documents,
                    top_n=min(self.top_n, len(docs)),
                    return_documents=False,
                    api_key=self.api_key,
                ),
                timeout=self.timeout_seconds,
            )
            reranked_docs = self._build_reranked_docs(docs, response)
            usage = self._extract_usage(response)
            logger.info(
                "rerank succeeded model=%s candidates=%s returned=%s total_tokens=%s",
                self.model_name,
                len(docs),
                len(reranked_docs),
                usage.get("total_tokens"),
            )
            return reranked_docs
        except Exception:
            logger.exception(
                "rerank failed model=%s candidates=%s fallback=%s",
                self.model_name,
                len(docs),
                self.fallback_to_retrieval,
            )
            if not self.fallback_to_retrieval:
                raise
            return docs[: min(self.top_n, len(docs))]

    def _build_reranked_docs(
        self, docs: list[Document], response: Any
    ) -> list[Document]:
        results = self._extract_results(response)
        if not results:
            raise ValueError("rerank returned empty results")

        reranked_docs: list[Document] = []
        seen_indexes: set[int] = set()
        for rank, item in enumerate(results, start=1):
            index = item.get("index")
            if not isinstance(index, int) or not (0 <= index < len(docs)):
                continue
            if index in seen_indexes:
                continue

            seen_indexes.add(index)
            doc = docs[index]
            metadata = dict(doc.metadata or {})
            metadata["rerank_score"] = item.get("relevance_score")
            metadata["rerank_rank"] = rank
            doc.metadata = metadata
            reranked_docs.append(doc)

        if not reranked_docs:
            raise ValueError("rerank results did not map to candidate documents")

        return reranked_docs

    @staticmethod
    def _extract_results(response: Any) -> list[dict[str, Any]]:
        if isinstance(response, dict):
            output = response.get("output") or {}
            results = output.get("results") or []
            return [item for item in results if isinstance(item, dict)]
        return []

    @staticmethod
    def _extract_usage(response: Any) -> dict[str, Any]:
        if isinstance(response, dict):
            usage = response.get("usage") or {}
            if isinstance(usage, dict):
                return usage
        return {}
