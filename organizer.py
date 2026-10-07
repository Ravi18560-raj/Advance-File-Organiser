"""Organizer: plans moves first, then executes them.

Splitting "plan" from "execute" gives us dry-run mode for free: a dry run
builds the exact same plan, it just never executes it. Every real move is
recorded in the journal so ``undo`` can reverse it later.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Iterable, List, Set

from . import journal
from .classifier import all_category_names, classify
from .models import FileRecord, MovePlan, RunResult
from .scanner import scan

logger = logging.getLogger(__name__)


def unique_destination(dest_dir: Path, filename: str, taken: Set[str]) -> Path:
    """Pick a path in ``dest_dir`` that is not used yet.

    ``taken`` holds lowercase paths already promised to other files in this
    plan, so two "report.pdf" files never collide: the second becomes
    "report (1).pdf".
    """
    candidate = dest_dir / filename
    stem, suffix = os.path.splitext(filename)
    counter = 1
    while str(candidate).lower() in taken or candidate.exists():
        candidate = dest_dir / f"{stem} ({counter}){suffix}"
        counter += 1
    return candidate


def plan_moves(records: Iterable[FileRecord], root: Path) -> List[MovePlan]:
    """Decide where every file goes. Pure planning: nothing is moved."""
    plan: List[MovePlan] = []
    taken: Set[str] = set()
    for record in sorted(records, key=lambda r: str(r.path)):
        category = classify(record)
        destination_dir = root / category
        if record.path.parent == destination_dir:
            continue  # already in the right folder
        destination = unique_destination(destination_dir, record.name, taken)
        taken.add(str(destination).lower())
        plan.append(MovePlan(source=record.path, destination=destination, category=category))
    return plan


def execute_plan(plan: List[MovePlan], root: Path, dry_run: bool = False) -> RunResult:
    """Carry out a plan (or pretend to, when ``dry_run`` is True)."""
    result = RunResult(dry_run=dry_run)
    if dry_run:
        result.moved = list(plan)
        return result

    try:
        for move in plan:
            try:
                if move.destination.exists():
                    # Planning checked this already; guard against races, because
                    # os.rename silently overwrites files on POSIX systems.
                    raise FileExistsError("destination appeared after planning")
                move.destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(move.source), str(move.destination))
            except OSError as exc:
                logger.error("Failed to move %s: %s", move.source, exc)
                result.failed.append((move, str(exc)))
                continue
            logger.info("Moved %s -> %s", move.source, move.destination)
            result.moved.append(move)
    finally:
        # Even if we are interrupted half-way, whatever DID move gets journaled.
        if result.moved:
            result.run_id = journal.append_run(root, result.moved)
    return result


def organize_directory(root: Path, recursive: bool = False, dry_run: bool = False) -> RunResult:
    """Scan ``root``, plan the moves and execute them."""
    root = Path(root).resolve()
    records = list(
        scan(root, recursive=recursive, exclude_top_level=frozenset(all_category_names()))
    )
    logger.info("Scanned %s: %d files found", root, len(records))
    plan = plan_moves(records, root)
    logger.info("Plan: %d files to move%s", len(plan), " (dry run)" if dry_run else "")
    return execute_plan(plan, root, dry_run=dry_run)
