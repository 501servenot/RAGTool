from functools import lru_cache
from io import BytesIO
from typing import BinaryIO, Literal

from fastapi import HTTPException, UploadFile, status
from pypdf import PdfReader
from starlette.concurrency import run_in_threadpool


SUPPORTED_EXTENSIONS = {"txt", "md", "pdf"}
ParserName = Literal["pypdf", "docling"]


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


def upload_extension(upload_file: UploadFile) -> str:
    ext = _get_extension(upload_file.filename)
    if ext in SUPPORTED_EXTENSIONS:
        return ext
    return {"text/plain": "txt", "text/markdown": "md", "text/x-markdown": "md",
            "application/pdf": "pdf"}.get(upload_file.content_type or "", ext)


@lru_cache(maxsize=4)
def _parse_pdf(raw: bytes, parser: ParserName) -> str:
    # Share the last four PDF results between preview and upload, in memory only.
    if parser == "docling":
        from app.utils.docling_reader import extract_with_docling

        return extract_with_docling(raw)
    return extract_text_from_pdf(BytesIO(raw))


async def read_upload_file(upload_file: UploadFile, parser: ParserName = "pypdf") -> str:
    if parser not in {"pypdf", "docling"}:
        raise HTTPException(status_code=400, detail="未知解析器")
    ext = upload_extension(upload_file)

    raw = await upload_file.read()

    try:
        if ext in {"txt", "md"}:
            return raw.decode("utf-8")
        if ext == "pdf":
            return await run_in_threadpool(_parse_pdf, raw, parser)
    except HTTPException:
        raise
    except UnicodeError as exc:
        raise HTTPException(status_code=400, detail="文本文件需使用 UTF-8 编码") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="PDF 解析失败，请检查文件是否损坏或加密") from exc

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"不支持的文件类型：{upload_file.filename}（仅支持 txt / md / pdf）",
    )
