"""Shared data shapes used by every module."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class FileRecord:
    """Everything we know about one file. Created by the scanner."""

    path: Path
    size: int
    extension: str  # lowercase, includes the dot; "" when the file has none
    modified: float  # POSIX timestamp
    category: Optional[str] = None  # filled in by the classifier
    hash: Optional[str] = None  # filled in by the duplicate finder

    @property
    def name(self) -> str:
        return self.path.name


@dataclass(frozen=True)
class MovePlan:
    """One planned move. Building plans never touches the disk."""

    source: Path
    destination: Path
    category: str


@dataclass
class RunResult:
    """Outcome of executing (or simulating) an organize run."""

    dry_run: bool = False
    run_id: Optional[str] = None
    moved: list[MovePlan] = field(default_factory=list)
    failed: list[tuple[MovePlan, str]] = field(default_factory=list)


@dataclass
class UndoResult:
    """Outcome of undoing (or simulating the undo of) a run."""

    run_id: str
    dry_run: bool = False
    restored: list[dict] = field(default_factory=list)
    failed: list[tuple[dict, str]] = field(default_factory=list)
