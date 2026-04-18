from __future__ import annotations

import subprocess

from common import WEB_DIR, frontend_package_manager, load_project_env


def main() -> None:
    env = load_project_env()
    host = env.get("FRONTEND_HOST", "0.0.0.0")
    port = env.get("FRONTEND_PORT", "5173")
    if not env.get("VITE_API_PROXY_TARGET"):
        env["VITE_API_PROXY_TARGET"] = "http://localhost:8000"

    manager = frontend_package_manager()
    command = manager + ["run", "dev", "--", "--host", host, "--port", port]
    subprocess.run(command, cwd=WEB_DIR, check=True, env=env)


if __name__ == "__main__":
    main()
