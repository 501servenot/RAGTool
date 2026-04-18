from __future__ import annotations

import subprocess
import sys
import venv
from pathlib import Path

from common import (
    ENV_EXAMPLE_FILE,
    ENV_FILE,
    ROOT_DIR,
    STORAGE_DIR,
    WEB_DIR,
    current_python,
    frontend_package_manager,
    venv_python,
)


def run_command(command: list[str], *, cwd: Path | None = None) -> None:
    print(f"$ {' '.join(command)}")
    subprocess.run(command, cwd=cwd or ROOT_DIR, check=True)


def ensure_env_file() -> None:
    if ENV_FILE.exists():
        print(f".env 已存在：{ENV_FILE}")
        return
    if not ENV_EXAMPLE_FILE.exists():
        raise FileNotFoundError(f"缺少模板文件：{ENV_EXAMPLE_FILE}")
    ENV_FILE.write_text(ENV_EXAMPLE_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"已创建 .env，请先填写必要配置：{ENV_FILE}")


def ensure_storage() -> None:
    (STORAGE_DIR / "chat_history").mkdir(parents=True, exist_ok=True)
    (STORAGE_DIR / "chroma_db").mkdir(parents=True, exist_ok=True)
    (STORAGE_DIR / "md5").mkdir(parents=True, exist_ok=True)
    (STORAGE_DIR / "md5" / "md5.txt").touch(exist_ok=True)


def ensure_venv() -> None:
    python_path = venv_python()
    if python_path.exists():
        print(f"虚拟环境已存在：{python_path}")
        return
    print("正在创建 .venv ...")
    venv.create(ROOT_DIR / ".venv", with_pip=True)


def install_backend_dependencies() -> None:
    python_path = str(venv_python())
    run_command([python_path, "-m", "pip", "install", "--upgrade", "pip"])
    run_command([python_path, "-m", "pip", "install", "-r", "requirements.txt"])


def install_frontend_dependencies() -> None:
    manager = frontend_package_manager()
    install_command = manager + ["install"]
    run_command(install_command, cwd=WEB_DIR)


def main() -> None:
    if sys.version_info < (3, 11):
        raise SystemExit("请使用 Python 3.11 或更高版本运行 bootstrap 脚本。")

    print("开始初始化项目 ...")
    ensure_env_file()
    ensure_storage()
    ensure_venv()
    install_backend_dependencies()
    install_frontend_dependencies()
    print("\n初始化完成。")
    print("下一步：")
    print("1. 编辑根目录 .env，填入 DASHSCOPE_API_KEY 等配置")
    print(f"2. 运行 `{current_python()} scripts/dev.py` 启动前后端")


if __name__ == "__main__":
    main()
