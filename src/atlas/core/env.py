from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


def load_project_env(project_root: Path | None = None) -> Path | None:
    """Load `.env` from project root (if present). Returns path when loaded."""
    root = project_root or Path.cwd()
    env_file = root / ".env"
    if env_file.is_file():
        load_dotenv(env_file)
        return env_file
    load_dotenv()
    return None
