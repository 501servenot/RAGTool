from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_kb_service
from app.schemas.knowledge import (
    DeleteKnowledgeDocumentResponse,
    KnowledgeBaseSummaryResponse,
)
from app.services.knowledge_base import KnowledgeBaseServer


router = APIRouter(tags=["knowledge"])


@router.get(
    "/knowledge-base/documents",
    response_model=KnowledgeBaseSummaryResponse,
    summary="查看当前知识库文档数量和列表",
)
async def get_knowledge_base_documents(
    kb: KnowledgeBaseServer = Depends(get_kb_service),
) -> KnowledgeBaseSummaryResponse:
    return KnowledgeBaseSummaryResponse(**kb.get_summary())


@router.delete(
    "/knowledge-base/documents/{document_id}",
    response_model=DeleteKnowledgeDocumentResponse,
    summary="删除指定知识库文档并同步移除向量数据",
)
async def delete_knowledge_base_document(
    document_id: str,
    kb: KnowledgeBaseServer = Depends(get_kb_service),
) -> DeleteKnowledgeDocumentResponse:
    result = kb.delete_document(document_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到对应的知识库文档",
        )

    return DeleteKnowledgeDocumentResponse(**result)
