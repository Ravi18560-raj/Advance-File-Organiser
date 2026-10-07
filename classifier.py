"""Classifier: maps a file extension to one of the category folders."""

from __future__ import annotations

from typing import List

from .config import CATEGORIES, OTHERS
from .models import FileRecord

# Reverse lookup built once: ".jpg" -> "Images". O(1) per file.
_EXTENSION_TO_CATEGORY = {
    extension: category
    for category, extensions in CATEGORIES.items()
    for extension in extensions
}


def classify_extension(extension: str) -> str:
    """Return the category for an extension such as '.PDF' (case-insensitive)."""
    return _EXTENSION_TO_CATEGORY.get(extension.lower(), OTHERS)


def classify(record: FileRecord) -> str:
    """Set and return ``record.category``."""
    record.category = classify_extension(record.extension)
    return record.category


def all_category_names() -> List[str]:
    """Every category folder name, including 'Others'."""
    return [*CATEGORIES, OTHERS]
