from fastapi import APIRouter

from app.api.v1.endpoints import chat, config, evaluate, knowledge, upload


api_router = APIRouter()
api_router.include_router(upload.router)
api_router.include_router(chat.router)
api_router.include_router(knowledge.router)
api_router.include_router(config.router)
api_router.include_router(evaluate.router)
