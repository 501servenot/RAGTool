from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_kb_service
from app.schemas.upload import ParsePreviewResponse, UploadResponse
from app.services.knowledge_base import KnowledgeBaseServer
from app.utils.file_reader import ParserName, read_upload_file, upload_extension


router = APIRouter(tags=["upload"])


@router.post("/upload/preview", response_model=ParsePreviewResponse, summary="预览解析结果（不入库）")
async def preview_file(
    file: UploadFile = File(...),
    parser: ParserName = Form("pypdf"),
) -> ParsePreviewResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="缺少文件名")
    text = await read_upload_file(file, parser)
    ext = upload_extension(file)
    return ParsePreviewResponse(
        filename=file.filename, parser=parser if ext == "pdf" else "text",
        format="markdown" if ext == "md" or (ext == "pdf" and parser == "docling") else "text",
        text=text, characters=len(text),
    )


@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="上传知识库文件（txt / md / pdf）",
)
async def upload_file(
    file: UploadFile = File(..., description="要上传的文本/Markdown/PDF 文件"),
    parser: ParserName = Form("pypdf"),
    kb: KnowledgeBaseServer = Depends(get_kb_service),
) -> UploadResponse:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="缺少文件名"
        )

    text = await read_upload_file(file, parser)
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="文件内容为空，无法写入知识库"
        )

    size_kb = (file.size or len(text.encode("utf-8"))) / 1024
    message = await run_in_threadpool(kb.upload_by_str, text, file.filename)

    return UploadResponse(
        filename=file.filename,
        size_kb=round(size_kb, 2),
        content_type=file.content_type or "",
        message=message,
        parser=parser if upload_extension(file) == "pdf" else "text",
    )
