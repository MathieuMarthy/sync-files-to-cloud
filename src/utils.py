import os.path

from config import ROOT_DIR


def path(relative_path: str) -> str:
    """Constructs an absolute path by joining the ROOT_DIR with the given relative path."""
    return os.path.join(ROOT_DIR, relative_path)
