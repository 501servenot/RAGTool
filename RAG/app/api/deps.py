from fastapi import Request

from app.services.knowledge_base import KnowledgeBaseServer
from app.services.chat_history import ChatHistoryService
from app.services.rag import RAGservice


def get_kb_service(request: Request) -> KnowledgeBaseServer:
    return request.app.state.kb_service


def get_rag_service(request: Request) -> RAGservice:
    return request.app.state.rag_service


def get_chat_history_service(request: Request) -> ChatHistoryService:
    return request.app.state.chat_history_service
