import json
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.deps import get_chat_history_service, get_rag_service
from app.schemas.chat import (
    ChatHistoryMessage,
    ChatRequest,
    ChatResponse,
    ChatSessionSummary,
    DeleteChatSessionResponse,
)
from app.services.chat_history import ChatHistoryService
from app.services.rag import RAGservice


router = APIRouter(tags=["chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="一次性返回完整回答（非流式）",
)
async def chat(
    payload: ChatRequest,
    rag: RAGservice = Depends(get_rag_service),
) -> ChatResponse:
    answer = await rag.invoke(payload.prompt, payload.session_id)
    return ChatResponse(answer=answer)


@router.get(
    "/chat/sessions",
    response_model=list[ChatSessionSummary],
    summary="获取历史会话列表",
)
async def get_chat_sessions(
    history_service: ChatHistoryService = Depends(get_chat_history_service),
) -> list[ChatSessionSummary]:
    return history_service.list_sessions()


@router.get(
    "/chat/sessions/{session_id}/messages",
    response_model=list[ChatHistoryMessage],
    summary="获取指定会话消息",
)
async def get_chat_session_messages(
    session_id: str,
    history_service: ChatHistoryService = Depends(get_chat_history_service),
) -> list[ChatHistoryMessage]:
    return history_service.get_session_messages(session_id)


@router.delete(
    "/chat/sessions/{session_id}",
    response_model=DeleteChatSessionResponse,
    summary="删除指定会话",
)
async def delete_chat_session(
    session_id: str,
    history_service: ChatHistoryService = Depends(get_chat_history_service),
) -> DeleteChatSessionResponse:
    try:
        return history_service.delete_session(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="会话不存在") from exc


@router.post(
    "/chat/stream",
    summary="SSE 流式输出回答",
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def chat_stream(
    payload: ChatRequest,
    rag: RAGservice = Depends(get_rag_service),
) -> StreamingResponse:
    async def event_generator() -> AsyncIterator[str]:
        try:
            async for token in rag.astream(payload.prompt, payload.session_id):
                yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
