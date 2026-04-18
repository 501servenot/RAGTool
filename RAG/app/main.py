from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.services.chat_history import ChatHistoryService
from app.services.knowledge_base import KnowledgeBaseServer
from app.services.rag import RAGservice


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_settings()
    app.state.kb_service = KnowledgeBaseServer()
    app.state.rag_service = RAGservice()
    app.state.chat_history_service = ChatHistoryService()
    try:
        yield
    finally:
        app.state.kb_service = None
        app.state.rag_service = None
        app.state.chat_history_service = None


app = FastAPI(
    title="RAG API",
    description="基于 FastAPI 的 RAG 服务：文件上传写入知识库 + 对话问答（支持 SSE 流式）",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["meta"], summary="健康检查")
async def health() -> dict[str, str]:
    return {"status": "ok"}
