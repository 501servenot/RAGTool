from __future__ import annotations

import subprocess

from common import BACKEND_DIR, load_project_env, venv_python


def main() -> None:
    env = load_project_env()
    host = env.get("BACKEND_HOST", "0.0.0.0")
    port = env.get("BACKEND_PORT", "8000")
    python_path = str(venv_python())
    command = [
        python_path,
        "-m",
        "uvicorn",
        "app.main:app",
        "--app-dir",
        str(BACKEND_DIR),
        "--reload",
        "--host",
        host,
        "--port",
        port,
    ]
    subprocess.run(command, check=True, env=env)


if __name__ == "__main__":
    main()
