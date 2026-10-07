"""Analyzer: statistics by extension/category and large-file detection."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List

from .classifier import classify_extension
from .models import FileRecord

NO_EXTENSION_LABEL = "(none)"


@dataclass
class GroupStat:
    """Count and total size for one group (an extension or a category)."""

    name: str
    count: int = 0
    total_size: int = 0


def _collect(records: Iterable[FileRecord], key_func) -> List[GroupStat]:
    stats: Dict[str, GroupStat] = {}
    for record in records:
        key = key_func(record)
        stat = stats.setdefault(key, GroupStat(name=key))
        stat.count += 1
        stat.total_size += record.size
    # Biggest first; name as a tie-breaker keeps output deterministic.
    return sorted(stats.values(), key=lambda s: (-s.total_size, -s.count, s.name))


def extension_stats(records: Iterable[FileRecord]) -> List[GroupStat]:
    """Count and total size per extension."""
    return _collect(records, lambda r: r.extension or NO_EXTENSION_LABEL)


def category_stats(records: Iterable[FileRecord]) -> List[GroupStat]:
    """Count and total size per category folder."""
    return _collect(records, lambda r: classify_extension(r.extension))


def find_large_files(records: Iterable[FileRecord], threshold_bytes: int) -> List[FileRecord]:
    """Files whose size is at least ``threshold_bytes``, largest first."""
    large = [record for record in records if record.size >= threshold_bytes]
    large.sort(key=lambda record: (-record.size, str(record.path)))
    return large


def total_size(records: Iterable[FileRecord]) -> int:
    return sum(record.size for record in records)
