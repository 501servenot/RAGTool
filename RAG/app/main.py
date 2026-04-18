from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.runtime import clear_runtime_services, initialize_runtime_services


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_runtime_services(app)
    try:
        yield
    finally:
        clear_runtime_services(app)


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
