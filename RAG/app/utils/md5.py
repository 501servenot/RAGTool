import hashlib
import os

from app.core.config import get_settings


def _ensure_md5_parent_dir() -> str:
    md5_file_path = get_settings().md5_file_path
    os.makedirs(os.path.dirname(md5_file_path), exist_ok=True)
    return md5_file_path


def string_to_md5(input_str: str, encoding: str = "utf-8") -> str:
    md5_obj = hashlib.md5()
    md5_obj.update(input_str.encode(encoding=encoding))
    return md5_obj.hexdigest()


def check_md5(md5_str: str) -> bool:
    md5_file_path = _ensure_md5_parent_dir()
    if not os.path.exists(md5_file_path):
        with open(md5_file_path, "w", encoding="utf-8"):
            pass
        return False
    with open(md5_file_path, "r", encoding="utf-8") as f:
        for line in f.readlines():
            if md5_str == line.strip():
                return True
    return False


def save_md5(md5_str: str) -> None:
    md5_file_path = _ensure_md5_parent_dir()
    with open(md5_file_path, "a", encoding="utf-8") as f:
        f.write(md5_str + "\n")


def remove_md5(md5_str: str) -> bool:
    md5_file_path = _ensure_md5_parent_dir()
    if not os.path.exists(md5_file_path):
        return False

    with open(md5_file_path, "r", encoding="utf-8") as f:
        items = [line.strip() for line in f.readlines() if line.strip()]

    if md5_str not in items:
        return False

    with open(md5_file_path, "w", encoding="utf-8") as f:
        for item in items:
            if item != md5_str:
                f.write(item + "\n")

    return True
