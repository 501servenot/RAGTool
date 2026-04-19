from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable

from app.core.config import get_settings
from app.core.model_factory import (
    create_chat_model,
    create_embedding_model,
    create_rerank_client,
)
from app.services.query_rewrite import QueryRewriteService
from app.services.rag import RAGservice
from app.services.rerank import RerankService
from app.services.vector_store import VectorStoreService


@dataclass(slots=True)
class EvaluationRuntime:
    config_snapshot: dict[str, Any]
    rag_service: Any


class EvaluationRuntimeFactory:
    def __init__(
        self,
        *,
        model_registry,
        embedding_factory: Callable[[Any], Any] = create_embedding_model,
        chat_factory: Callable[[Any], Any] = create_chat_model,
        rerank_client_factory: Callable[[Any], Any] = create_rerank_client,
        vector_service_factory: Callable[[Any], Any] = VectorStoreService,
        query_rewrite_factory: Callable[[Any], Any] = QueryRewriteService,
        rerank_service_factory: Callable[[Any, str], Any] = lambda client, model_name: RerankService(
            client=client,
            model_name=model_name,
        ),
        rag_service_factory: Callable[..., Any] = RAGservice,
    ):
        self.model_registry = model_registry
        self.embedding_factory = embedding_factory
        self.chat_factory = chat_factory
        self.rerank_client_factory = rerank_client_factory
        self.vector_service_factory = vector_service_factory
        self.query_rewrite_factory = query_rewrite_factory
        self.rerank_service_factory = rerank_service_factory
        self.rag_service_factory = rag_service_factory

    def create_runtime(
        self,
        *,
        config_overrides: dict[str, Any] | None = None,
    ) -> EvaluationRuntime:
        overrides = dict(config_overrides or {})
        embedding_config = self.model_registry.get_assignment("embedding")
        chat_config = self.model_registry.get_assignment("chat")
        rewrite_config = self.model_registry.get_assignment("rewrite")
        rerank_config = self.model_registry.get_assignment("rerank")

        embedding_model = self.embedding_factory(embedding_config)
        vector_service = self.vector_service_factory(embedding_model)
        chat_model = self.chat_factory(chat_config)
        rewrite_model = self.chat_factory(rewrite_config)
        rerank_client = self.rerank_client_factory(rerank_config)
        rerank_model_name = getattr(rerank_config, "model", None) or rerank_config.get(
            "model", ""
        )
        rag_service = self.rag_service_factory(
            vector_service=vector_service,
            chat_model=chat_model,
            query_rewrite_service=self.query_rewrite_factory(chat_model=rewrite_model),
            rerank_service=self.rerank_service_factory(
                rerank_client,
                rerank_model_name,
            ),
        )
        self._apply_overrides(rag_service, vector_service, overrides)
        return EvaluationRuntime(config_snapshot=overrides, rag_service=rag_service)

    @staticmethod
    def _apply_overrides(rag_service: Any, vector_service: Any, overrides: dict[str, Any]) -> None:
        if not overrides:
            return

        if hasattr(rag_service, "settings"):
            updated_settings = deepcopy(get_settings())
            for key, value in overrides.items():
                if hasattr(updated_settings, key):
                    setattr(updated_settings, key, value)
            rag_service.settings = updated_settings

        if hasattr(vector_service, "get_retriever"):
            original_get_retriever = vector_service.get_retriever

            def get_retriever(top_k: int | None = None):
                effective_top_k = top_k
                if effective_top_k is None and "retrieve_top_k" in overrides:
                    effective_top_k = overrides["retrieve_top_k"]
                return original_get_retriever(top_k=effective_top_k)

            vector_service.get_retriever = get_retriever

        if hasattr(vector_service, "expand_with_neighbors"):
            original_expand = vector_service.expand_with_neighbors

            def expand_with_neighbors(docs, *, neighbor_window: int | None = None):
                effective_window = neighbor_window
                if (
                    effective_window is None
                    and "retrieval_neighbor_chunks" in overrides
                ):
                    effective_window = overrides["retrieval_neighbor_chunks"]
                return original_expand(docs, neighbor_window=effective_window)

            vector_service.expand_with_neighbors = expand_with_neighbors
