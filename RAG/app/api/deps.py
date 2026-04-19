from fastapi import Request

from app.services.knowledge_base import KnowledgeBaseServer
from app.services.chat_history import ChatHistoryService
from app.services.rag import RAGservice
from evaluate.dataset_generator import EvaluationDatasetGenerator
from evaluate.ragas_runner import RagasEvaluationRunner
from evaluate.repository import FileEvaluationRepository
from evaluate.runtime_factory import EvaluationRuntimeFactory
from evaluate.task_manager import EvaluationTaskManager


def get_kb_service(request: Request) -> KnowledgeBaseServer:
    return request.app.state.kb_service


def get_rag_service(request: Request) -> RAGservice:
    return request.app.state.rag_service


def get_chat_history_service(request: Request) -> ChatHistoryService:
    return request.app.state.chat_history_service


def get_evaluation_repository(request: Request) -> FileEvaluationRepository:
    return request.app.state.evaluation_repository


def get_evaluation_task_manager(request: Request) -> EvaluationTaskManager:
    return request.app.state.evaluation_task_manager


def get_dataset_generator(request: Request) -> EvaluationDatasetGenerator:
    return request.app.state.dataset_generator


def get_ragas_runner(request: Request) -> RagasEvaluationRunner:
    return request.app.state.ragas_runner


def get_evaluation_runtime_factory(request: Request) -> EvaluationRuntimeFactory:
    return request.app.state.evaluation_runtime_factory
