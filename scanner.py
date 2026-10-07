"""Scanner: walks a folder and yields FileRecord objects.

The scanner only *reads* the file system. It never classifies, hashes or
moves anything, which keeps every other module easy to test.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import AbstractSet, Iterator

from .models import FileRecord

logger = logging.getLogger(__name__)


def scan(
    root: Path,
    recursive: bool = True,
    exclude_top_level: AbstractSet[str] = frozenset(),
) -> Iterator[FileRecord]:
    """Yield a FileRecord for every regular file under ``root``.

    - Hidden files and folders (names starting with ".") are always skipped.
      This also keeps the tool's own ``.sfm`` state folder out of every scan.
    - Symbolic links are never followed, which avoids loops and surprises.
    - ``exclude_top_level`` names folders directly inside ``root`` to skip
      (the organizer uses this to avoid re-scanning Images/, Videos/, ...).
    - Unreadable folders or files are logged and skipped, not fatal.
    """
    root = Path(root)
    pending = [root]

    while pending:
        current = pending.pop()
        try:
            with os.scandir(current) as iterator:
                entries = sorted(iterator, key=lambda entry: entry.name)
        except OSError as exc:
            logger.warning("Cannot read folder %s: %s", current, exc)
            continue

        for entry in entries:
            if entry.name.startswith("."):
                continue
            try:
                if entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    if not recursive:
                        continue
                    if current == root and entry.name in exclude_top_level:
                        continue
                    pending.append(Path(entry.path))
                    continue
                if not entry.is_file(follow_symlinks=False):
                    continue
                info = entry.stat(follow_symlinks=False)
            except OSError as exc:
                logger.warning("Cannot read %s: %s", entry.path, exc)
                continue

            yield FileRecord(
                path=Path(entry.path),
                size=info.st_size,
                extension=os.path.splitext(entry.name)[1].lower(),
                modified=info.st_mtime,
            )
