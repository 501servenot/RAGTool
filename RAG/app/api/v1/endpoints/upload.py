from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import get_kb_service
from app.schemas.upload import UploadResponse
from app.services.knowledge_base import KnowledgeBaseServer
from app.utils.file_reader import read_upload_file


router = APIRouter(tags=["upload"])


@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="上传知识库文件（txt / md / pdf）",
)
async def upload_file(
    file: UploadFile = File(..., description="要上传的文本/Markdown/PDF 文件"),
    kb: KnowledgeBaseServer = Depends(get_kb_service),
) -> UploadResponse:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="缺少文件名"
        )

    text = await read_upload_file(file)
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="文件内容为空，无法写入知识库"
        )

    size_kb = (file.size or len(text.encode("utf-8"))) / 1024
    message = kb.upload_by_str(text, file.filename)

    return UploadResponse(
        filename=file.filename,
        size_kb=round(size_kb, 2),
        content_type=file.content_type or "",
        message=message,
    )
