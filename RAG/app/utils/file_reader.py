from typing import BinaryIO

from fastapi import HTTPException, UploadFile, status
from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {"txt", "md", "pdf"}


def _get_extension(filename: str | None) -> str:
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def extract_text_from_pdf(pdf_file: BinaryIO) -> str:
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += (page.extract_text() or "") + "\n"
    return text


async def read_upload_file(upload_file: UploadFile) -> str:
    ext = _get_extension(upload_file.filename)
    content_type = upload_file.content_type or ""

    raw = await upload_file.read()

    if ext == "txt" or content_type == "text/plain":
        return raw.decode("utf-8")
    if ext == "md" or content_type in {"text/markdown", "text/x-markdown"}:
        return raw.decode("utf-8")
    if ext == "pdf" or content_type == "application/pdf":
        from io import BytesIO

        return extract_text_from_pdf(BytesIO(raw))

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"不支持的文件类型：{upload_file.filename}（仅支持 txt / md / pdf）",
    )
