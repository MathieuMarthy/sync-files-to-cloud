import hashlib
import os.path
from pathlib import Path

from config import ROOT_DIR


def path(relative_path: str) -> str:
    """Constructs an absolute path by joining the ROOT_DIR with the given relative path."""
    return os.path.join(ROOT_DIR, relative_path)


def calculate_md5(file_path: Path) -> str:
    """Calculate MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()
