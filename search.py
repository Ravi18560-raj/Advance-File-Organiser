"""Search: filter FileRecords by name, extension, category, size and date."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from typing import FrozenSet, Iterable, List, Optional

from .classifier import classify_extension
from .models import FileRecord

_GLOB_CHARS = "*?["


@dataclass
class SearchCriteria:
    """All filters are optional; a file must satisfy every filter given."""

    name: Optional[str] = None  # substring, or a glob like "report*.pdf"
    extensions: Optional[Iterable[str]] = None  # "py" and ".PY" both work
    category: Optional[str] = None
    min_size: Optional[int] = None  # bytes, inclusive
    max_size: Optional[int] = None  # bytes, inclusive
    modified_after: Optional[float] = None  # timestamp, inclusive
    modified_before: Optional[float] = None  # timestamp, exclusive

    def __post_init__(self) -> None:
        if self.extensions is not None:
            self.extensions = frozenset(
                ext.lower() if ext.startswith(".") else f".{ext.lower()}"
                for ext in self.extensions
            )
        if self.category is not None:
            self.category = self.category.lower()


def _name_matches(filename: str, pattern: str) -> bool:
    filename, pattern = filename.lower(), pattern.lower()
    if any(char in pattern for char in _GLOB_CHARS):
        return fnmatch.fnmatchcase(filename, pattern)
    return pattern in filename


def matches(record: FileRecord, criteria: SearchCriteria) -> bool:
    """True when ``record`` satisfies every filter in ``criteria``."""
    if criteria.name is not None and not _name_matches(record.name, criteria.name):
        return False
    extensions: Optional[FrozenSet[str]] = criteria.extensions  # type: ignore[assignment]
    if extensions is not None and record.extension not in extensions:
        return False
    if criteria.category is not None:
        if classify_extension(record.extension).lower() != criteria.category:
            return False
    if criteria.min_size is not None and record.size < criteria.min_size:
        return False
    if criteria.max_size is not None and record.size > criteria.max_size:
        return False
    if criteria.modified_after is not None and record.modified < criteria.modified_after:
        return False
    if criteria.modified_before is not None and record.modified >= criteria.modified_before:
        return False
    return True


def search(records: Iterable[FileRecord], criteria: SearchCriteria) -> List[FileRecord]:
    """Return matching records sorted by path."""
    found = [record for record in records if matches(record, criteria)]
    found.sort(key=lambda record: str(record.path))
    return found
