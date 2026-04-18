from fastapi import FastAPI

from app.core.config import get_settings
from app.core.model_factory import (
    create_chat_model,
    create_embedding_model,
    create_rerank_client,
)
from app.core.model_registry import get_model_registry
from app.services.chat_history import ChatHistoryService
from app.services.knowledge_base import KnowledgeBaseServer
from app.services.query_rewrite import QueryRewriteService
from app.services.rag import RAGservice
from app.services.rerank import RerankService
from app.services.vector_store import VectorStoreService


def initialize_runtime_services(app: FastAPI) -> None:
    settings = get_settings()
    registry = get_model_registry(
        registry_path=settings.model_registry_path,
    )

    embedding_config = registry.get_assignment("embedding")
    chat_config = registry.get_assignment("chat")
    rewrite_config = registry.get_assignment("rewrite")
    rerank_config = registry.get_assignment("rerank")

    embedding_model = create_embedding_model(embedding_config)
    vector_service = VectorStoreService(embedding=embedding_model)
    chat_model = create_chat_model(chat_config)
    rewrite_model = create_chat_model(rewrite_config)
    rerank_client = create_rerank_client(rerank_config)

    app.state.model_registry = registry
    app.state.kb_service = KnowledgeBaseServer(embedding=embedding_model)
    app.state.rag_service = RAGservice(
        vector_service=vector_service,
        chat_model=chat_model,
        query_rewrite_service=QueryRewriteService(chat_model=rewrite_model),
        rerank_service=RerankService(
            client=rerank_client,
            model_name=rerank_config.model,
        ),
    )
    app.state.chat_history_service = ChatHistoryService()


def clear_runtime_services(app: FastAPI) -> None:
    app.state.model_registry = None
    app.state.kb_service = None
    app.state.rag_service = None
    app.state.chat_history_service = None


def reload_runtime_services(app: FastAPI) -> None:
    clear_runtime_services(app)
    initialize_runtime_services(app)
