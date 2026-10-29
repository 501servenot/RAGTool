"""Optional Docling adapter. Run in an isolated interpreter to avoid dependency conflicts."""
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Lock

from fastapi import HTTPException

from app.core.config import get_settings

_lock = Lock()
logger = logging.getLogger(__name__)


def extract_with_docling(raw: bytes) -> str:
    settings = get_settings()
    python = settings.docling_python or sys.executable
    env = os.environ.copy()
    if settings.docling_model_cache:
        env["HF_HOME"] = settings.docling_model_cache
    env.setdefault("HF_HUB_DISABLE_XET", "1")
    env.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    with _lock, tempfile.TemporaryDirectory(prefix="ragtool-docling-") as temp:
        folder = Path(temp)
        source, output = folder / "input.pdf", folder / "output.md"
        source.write_bytes(raw)
        try:
            with (folder / "worker.log").open("wb") as log:
                result = subprocess.run(
                    [python, "-X", "utf8", str(Path(__file__).with_name("docling_worker.py")),
                     str(source), str(output)],
                    stdout=log, stderr=log, env=env, timeout=600,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
        except OSError as exc:
            raise HTTPException(status_code=503, detail="Docling 环境不可用，请检查 DOCLING_PYTHON 配置") from exc
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(status_code=504, detail="Docling 解析超过 10 分钟，请缩小文件后重试") from exc
        if result.returncode == 42:
            raise HTTPException(status_code=503, detail="尚未安装 Docling，请按 README 安装可选解析器依赖")
        if result.returncode != 0 or not output.exists():
            logger.error("Docling failed: %s", (folder / "worker.log").read_text(encoding="utf-8", errors="replace")[-4000:])
            raise HTTPException(status_code=422, detail="Docling 解析失败，请检查文件和模型下载连接，或改用 pypdf")
        return output.read_text(encoding="utf-8")
