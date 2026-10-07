"""Journal: a JSON file that remembers every organize run so it can be undone.

The journal lives in ``<folder>/.sfm/journal.json`` and stores paths *relative*
to the organized folder, so undo still works if the folder is renamed or moved.
"""

from __future__ import annotations

import json
import logging
import os
import secrets
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .config import JOURNAL_FILE_NAME, STATE_DIR_NAME
from .models import MovePlan

logger = logging.getLogger(__name__)


class JournalError(Exception):
    """The journal file exists but cannot be read."""


def journal_path(root: Path) -> Path:
    return Path(root) / STATE_DIR_NAME / JOURNAL_FILE_NAME


def load_runs(root: Path) -> List[Dict]:
    path = journal_path(root)
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            runs = json.load(handle)
    except (json.JSONDecodeError, OSError) as exc:
        raise JournalError(f"Cannot read journal {path}: {exc}") from exc
    if not isinstance(runs, list):
        raise JournalError(f"Journal {path} is not in the expected format")
    return runs


def _save_runs(root: Path, runs: List[Dict]) -> None:
    path = journal_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(runs, handle, indent=2)
    os.replace(temp, path)  # atomic: a crash never leaves a half-written journal


def _new_run_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2)


def append_run(root: Path, moves: List[MovePlan]) -> Optional[str]:
    """Record a finished run and return its id (None if nothing moved)."""
    if not moves:
        return None
    root = Path(root)
    run = {
        "id": _new_run_id(),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "moves": [
            {
                "source": move.source.relative_to(root).as_posix(),
                "destination": move.destination.relative_to(root).as_posix(),
            }
            for move in moves
        ],
    }
    runs = load_runs(root)
    runs.append(run)
    _save_runs(root, runs)
    logger.info("Journal: recorded run %s (%d moves)", run["id"], len(moves))
    return run["id"]


def last_run(root: Path) -> Optional[Dict]:
    runs = load_runs(root)
    return runs[-1] if runs else None


def update_run(root: Path, run_id: str, remaining_moves: List[Dict]) -> None:
    """Keep only ``remaining_moves`` for a run; drop the run when none are left."""
    runs = load_runs(root)
    updated: List[Dict] = []
    for run in runs:
        if run["id"] == run_id:
            if not remaining_moves:
                continue
            run = {**run, "moves": remaining_moves}
        updated.append(run)
    _save_runs(root, updated)
