"""Compatibility command: Daily Brief now lives in the sibling project."""
import runpy
import sys
from pathlib import Path

target = Path(__file__).resolve().parents[3] / "daily-brief" / "scripts" / "standalone_news.py"
if not target.is_file():
    raise SystemExit("Daily Brief moved to ../daily-brief; use that project's scripts.")
sys.path.insert(0, str(target.parents[1]))
runpy.run_path(str(target), run_name="__main__")
