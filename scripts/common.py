from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "RAG"
WEB_DIR = ROOT_DIR / "web"
ENV_FILE = ROOT_DIR / ".env"
ENV_EXAMPLE_FILE = ROOT_DIR / ".env.example"
STORAGE_DIR = ROOT_DIR / "storage"


def read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'").strip('"')
    return values


def load_project_env() -> dict[str, str]:
    env = dict(os.environ)
    env.update(read_env_file(ENV_FILE))
    return env


def venv_python() -> Path:
    if os.name == "nt":
        return ROOT_DIR / ".venv" / "Scripts" / "python.exe"
    return ROOT_DIR / ".venv" / "bin" / "python"


def ensure_command(command_name: str) -> str | None:
    return shutil.which(command_name)


def frontend_package_manager() -> list[str]:
    if ensure_command("pnpm") and (WEB_DIR / "pnpm-lock.yaml").exists():
        return ["pnpm"]
    if ensure_command("npm"):
        return ["npm"]
    raise RuntimeError("未找到 pnpm 或 npm，请先安装 Node.js（推荐 Node.js 20+）。")


def current_python() -> str:
    return sys.executable
