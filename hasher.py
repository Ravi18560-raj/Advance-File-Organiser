"""Hasher: fingerprints files without loading them fully into memory."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

from .config import HASH_ALGORITHM, HASH_CHUNK_SIZE, PARTIAL_HASH_BYTES


def hash_file(
    path: Path,
    chunk_size: int = HASH_CHUNK_SIZE,
    max_bytes: Optional[int] = None,
    algorithm: str = HASH_ALGORITHM,
) -> str:
    """Return the hex digest of a file, reading it in chunks.

    ``max_bytes`` limits hashing to the first N bytes, which is how the
    duplicate finder performs its cheap "quick check".
    """
    digest = hashlib.new(algorithm)
    remaining = max_bytes
    with open(path, "rb") as handle:
        while True:
            to_read = chunk_size if remaining is None else min(chunk_size, remaining)
            if to_read <= 0:
                break
            chunk = handle.read(to_read)
            if not chunk:
                break
            digest.update(chunk)
            if remaining is not None:
                remaining -= len(chunk)
    return digest.hexdigest()


def quick_hash(path: Path) -> str:
    """Hash only the first PARTIAL_HASH_BYTES of a file."""
    return hash_file(path, max_bytes=PARTIAL_HASH_BYTES)
