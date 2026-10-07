"""Duplicate detection using a three-stage filter.

Hashing every file is slow, so we only hash when it could still matter:

1. Group by size.     Different sizes can never be identical (almost free).
2. Group by quick hash of the first 64 KB.  Cheap, removes most look-alikes.
3. Group by full hash. Only for the few files that survived stages 1 and 2.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional

from .config import PARTIAL_HASH_BYTES
from .hasher import hash_file, quick_hash
from .models import FileRecord

logger = logging.getLogger(__name__)


@dataclass
class DuplicateGroup:
    """A set of byte-for-byte identical files."""

    hash: str
    size: int
    files: List[FileRecord]

    @property
    def wasted_bytes(self) -> int:
        """Space you would recover by keeping just one copy."""
        return self.size * (len(self.files) - 1)


def _safe_hash(record: FileRecord, hasher: Callable) -> Optional[str]:
    try:
        return hasher(record.path)
    except OSError as exc:
        logger.warning("Cannot hash %s: %s", record.path, exc)
        return None


def _bucket(records: Iterable[FileRecord], hasher: Callable) -> Dict[str, List[FileRecord]]:
    buckets: Dict[str, List[FileRecord]] = defaultdict(list)
    for record in records:
        digest = _safe_hash(record, hasher)
        if digest is not None:
            buckets[digest].append(record)
    return buckets


def find_duplicates(records: Iterable[FileRecord], min_size: int = 1) -> List[DuplicateGroup]:
    """Return groups of identical files, biggest space-waster first.

    Empty files are ignored by default (``min_size=1``): all empty files are
    "identical", which is true but not useful.
    """
    by_size: Dict[int, List[FileRecord]] = defaultdict(list)
    for record in records:
        if record.size >= min_size:
            by_size[record.size].append(record)

    groups: List[DuplicateGroup] = []
    for size, same_size in by_size.items():
        if len(same_size) < 2:
            continue  # stage 1: a unique size cannot have a duplicate

        for quick_digest, quick_group in _bucket(same_size, quick_hash).items():
            if len(quick_group) < 2:
                continue  # stage 2: first 64 KB differs (or file is unique)

            if size <= PARTIAL_HASH_BYTES:
                # The quick hash already covered the entire file.
                confirmed = {quick_digest: quick_group}
            else:
                confirmed = _bucket(quick_group, hash_file)  # stage 3

            for digest, members in confirmed.items():
                if len(members) < 2:
                    continue
                for member in members:
                    member.hash = digest
                members.sort(key=lambda record: str(record.path))
                groups.append(DuplicateGroup(hash=digest, size=size, files=members))

    groups.sort(key=lambda group: (-group.wasted_bytes, group.hash))
    return groups
