from pathlib import Path

from smart_file_manager.analyzer import (
    category_stats,
    extension_stats,
    find_large_files,
    total_size,
)
from smart_file_manager.models import FileRecord


def rec(name, size):
    path = Path(name)
    return FileRecord(path=path, size=size, extension=path.suffix.lower(), modified=0.0)


RECORDS = [
    rec("a.jpg", 100),
    rec("b.JPG", 300),
    rec("c.pdf", 50),
    rec("d.py", 10),
    rec("noext", 5),
]


def test_extension_stats_sorted_by_size():
    stats = extension_stats(RECORDS)
    assert [s.name for s in stats] == [".jpg", ".pdf", ".py", "(none)"]
    jpg = stats[0]
    assert jpg.count == 2 and jpg.total_size == 400


def test_category_stats():
    stats = {s.name: s for s in category_stats(RECORDS)}
    assert stats["Images"].count == 2 and stats["Images"].total_size == 400
    assert stats["Documents"].total_size == 50
    assert stats["Code"].count == 1
    assert stats["Others"].count == 1  # the file without an extension


def test_large_files_threshold_is_inclusive_and_sorted():
    large = find_large_files(RECORDS, threshold_bytes=100)
    assert [r.name for r in large] == ["b.JPG", "a.jpg"]


def test_large_files_none_found():
    assert find_large_files(RECORDS, threshold_bytes=10_000) == []


def test_total_size():
    assert total_size(RECORDS) == 465
    assert total_size([]) == 0
