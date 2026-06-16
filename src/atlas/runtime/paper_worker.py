"""Background paper/live bot — started from dashboard or CLI."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def main() -> None:
    parser = argparse.ArgumentParser(description="ATLAS paper/live worker")
    parser.add_argument("--config", required=True, help="Path to YAML config (relative to project root)")
    args = parser.parse_args()

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))

    from atlas.core.config import load_config
    from atlas.core.env import load_project_env
    from atlas.runtime.runner import TradingRunner

    load_project_env(PROJECT_ROOT)
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path

    log_path = PROJECT_ROOT / "data" / "runtime" / "paper_bot.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("a", encoding="utf-8")
    sys.stdout = log_file
    sys.stderr = log_file

    runner = TradingRunner(load_config(config_path))
    runner.run()


if __name__ == "__main__":
    main()
