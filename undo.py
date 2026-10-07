"""Undo: reverse the most recent organize run using the journal."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from . import journal
from .classifier import all_category_names
from .models import UndoResult

logger = logging.getLogger(__name__)


def _remove_empty_category_folders(root: Path) -> None:
    """Tidy up Images/, Videos/, ... if undoing left them empty."""
    for name in all_category_names():
        folder = root / name
        if folder.is_dir():
            try:
                folder.rmdir()  # only succeeds when the folder is empty
            except OSError:
                pass


def undo_last_run(root: Path, dry_run: bool = False) -> Optional[UndoResult]:
    """Move files back to where they were. Returns None if there is nothing to undo.

    Moves are reversed in the opposite order they happened. A move that cannot
    be undone because the original spot is taken stays in the journal so you
    can fix the conflict and try again. A move whose file has vanished is
    dropped, since retrying could never succeed.
    """
    root = Path(root).resolve()
    run = journal.last_run(root)
    if run is None:
        return None

    result = UndoResult(run_id=run["id"], dry_run=dry_run)
    still_pending: List[Dict] = []

    for move in reversed(run["moves"]):
        original = root / move["source"]
        organized = root / move["destination"]

        if not organized.exists():
            result.failed.append((move, "file is no longer at its organized location"))
            continue
        if original.exists():
            result.failed.append((move, "something already exists at the original location"))
            still_pending.append(move)
            continue
        if dry_run:
            result.restored.append(move)
            continue

        try:
            original.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(organized), str(original))
        except OSError as exc:
            logger.error("Failed to restore %s: %s", organized, exc)
            result.failed.append((move, str(exc)))
            still_pending.append(move)
            continue
        logger.info("Restored %s -> %s", organized, original)
        result.restored.append(move)

    if not dry_run:
        journal.update_run(root, run["id"], list(reversed(still_pending)))
        _remove_empty_category_folders(root)
    return result
