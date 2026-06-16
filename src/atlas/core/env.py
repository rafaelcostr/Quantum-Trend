from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


def load_project_env(project_root: Path | None = None) -> Path | None:
    """Load `.env` from project root (if present). Returns path when loaded."""
    root = project_root or Path.cwd()
    env_file = root / ".env"
    if env_file.is_file():
        load_dotenv(env_file, override=True)
        return env_file
    load_dotenv(override=True)
    return None


def find_project_root(start: Path | None = None) -> Path:
    """Walk up from start (or cwd) until pyproject.toml or .env is found."""
    current = (start or Path.cwd()).resolve()
    for path in [current, *current.parents]:
        if (path / "pyproject.toml").is_file() or (path / ".env").is_file():
            return path
    return current
