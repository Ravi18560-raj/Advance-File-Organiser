from pathlib import Path

from smart_file_manager.models import FileRecord
from smart_file_manager.search import SearchCriteria, search


def rec(name, size=10, modified=1000.0):
    path = Path(name)
    return FileRecord(path=path, size=size, extension=path.suffix.lower(), modified=modified)


RECORDS = [
    rec("Invoice_March.pdf", size=500, modified=1000),
    rec("invoice_april.PDF", size=900, modified=2000),
    rec("holiday.jpg", size=4000, modified=3000),
    rec("notes.txt", size=20, modified=4000),
    rec("main.py", size=300, modified=5000),
]


def found(**kwargs):
    return [r.name for r in search(RECORDS, SearchCriteria(**kwargs))]


def test_no_filters_returns_everything_sorted():
    assert found() == sorted(r.name for r in RECORDS)


def test_name_substring_is_case_insensitive():
    assert found(name="INVOICE") == ["Invoice_March.pdf", "invoice_april.PDF"]


def test_name_glob():
    assert found(name="*.txt") == ["notes.txt"]
    assert found(name="invoice_*.pdf") == ["Invoice_March.pdf", "invoice_april.PDF"]


def test_extensions_with_or_without_dot_and_any_case():
    assert found(extensions=["pdf"]) == ["Invoice_March.pdf", "invoice_april.PDF"]
    assert found(extensions=[".PY", "txt"]) == ["main.py", "notes.txt"]


def test_category():
    assert found(category="Images") == ["holiday.jpg"]
    assert found(category="documents") == ["Invoice_March.pdf", "invoice_april.PDF", "notes.txt"]


def test_size_range_is_inclusive():
    assert found(min_size=500, max_size=900) == ["Invoice_March.pdf", "invoice_april.PDF"]


def test_modified_after_inclusive_before_exclusive():
    assert found(modified_after=3000) == ["holiday.jpg", "main.py", "notes.txt"]
    assert found(modified_before=3000) == ["Invoice_March.pdf", "invoice_april.PDF"]


def test_filters_combine_with_and():
    assert found(name="invoice", min_size=600) == ["invoice_april.PDF"]
    assert found(category="Documents", modified_after=2000, max_size=100) == ["notes.txt"]


def test_no_match():
    assert found(name="does-not-exist") == []
