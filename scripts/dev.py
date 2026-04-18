from __future__ import annotations

import signal
import subprocess
import sys
import time

from common import ROOT_DIR, current_python


def main() -> None:
    python_path = current_python()
    processes = [
        subprocess.Popen([python_path, "scripts/start_backend.py"], cwd=ROOT_DIR),
        subprocess.Popen([python_path, "scripts/start_frontend.py"], cwd=ROOT_DIR),
    ]

    try:
        while True:
            exit_codes = [process.poll() for process in processes]
            if any(code is not None for code in exit_codes):
                for process in processes:
                    if process.poll() is None:
                        process.terminate()
                raise SystemExit(
                    f"检测到子进程退出，exit codes: {exit_codes}"
                )
            time.sleep(1)
    except KeyboardInterrupt:
        for process in processes:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
        time.sleep(1)
        for process in processes:
            if process.poll() is None:
                process.terminate()
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()


if __name__ == "__main__":
    sys.exit(main())
