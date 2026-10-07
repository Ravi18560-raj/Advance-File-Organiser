"""Small helpers for sizes and dates, shared by the CLI and the search module."""

from __future__ import annotations

import re
from datetime import datetime

_UNITS = ["B", "KB", "MB", "GB", "TB"]

_MULTIPLIERS = {
    "": 1, "b": 1,
    "k": 1024, "kb": 1024,
    "m": 1024 ** 2, "mb": 1024 ** 2,
    "g": 1024 ** 3, "gb": 1024 ** 3,
    "t": 1024 ** 4, "tb": 1024 ** 4,
}

_SIZE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([a-z]*)\s*$", re.IGNORECASE)


def format_size(num_bytes: int) -> str:
    """Turn a byte count into a short human-readable string (1024-based)."""
    size = float(num_bytes)
    for unit in _UNITS:
        if size < 1024 or unit == _UNITS[-1]:
            if unit == "B":
                return f"{int(size)} B"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{int(num_bytes)} B"  # pragma: no cover (loop always returns)


def parse_size(text: str) -> int:
    """Parse '500', '10KB', '1.5 GB' ... into a number of bytes."""
    match = _SIZE_RE.match(text)
    if not match:
        raise ValueError(f"Invalid size {text!r} (examples: 500, 10KB, 1.5GB)")
    number, unit = match.groups()
    unit = unit.lower()
    if unit not in _MULTIPLIERS:
        raise ValueError(f"Unknown size unit {unit!r} in {text!r} (use KB, MB, GB or TB)")
    return int(float(number) * _MULTIPLIERS[unit])


def parse_date(text: str) -> float:
    """Parse 'YYYY-MM-DD' into a local-midnight POSIX timestamp."""
    try:
        return datetime.strptime(text.strip(), "%Y-%m-%d").timestamp()
    except ValueError:
        raise ValueError(f"Invalid date {text!r}; use YYYY-MM-DD") from None


def format_timestamp(timestamp: float) -> str:
    """Format a POSIX timestamp for display."""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
