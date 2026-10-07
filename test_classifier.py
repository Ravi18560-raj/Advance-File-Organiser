from pathlib import Path

import pytest

from smart_file_manager.classifier import all_category_names, classify, classify_extension
from smart_file_manager.config import CATEGORIES, OTHERS
from smart_file_manager.models import FileRecord


@pytest.mark.parametrize("extension, category", [
    (".jpg", "Images"),
    (".png", "Images"),
    (".mp4", "Videos"),
    (".mkv", "Videos"),
    (".pdf", "Documents"),
    (".docx", "Documents"),
    (".py", "Code"),
    (".json", "Code"),
    (".zip", "Archives"),
    (".gz", "Archives"),
    (".xyz", OTHERS),
    ("", OTHERS),
])
def test_classify_extension(extension, category):
    assert classify_extension(extension) == category


def test_classification_is_case_insensitive():
    assert classify_extension(".JPG") == "Images"
    assert classify_extension(".Pdf") == "Documents"


def test_classify_sets_record_category():
    record = FileRecord(path=Path("a.py"), size=1, extension=".py", modified=0.0)
    assert classify(record) == "Code"
    assert record.category == "Code"


def test_no_extension_belongs_to_two_categories():
    seen = {}
    for category, extensions in CATEGORIES.items():
        for extension in extensions:
            assert extension == extension.lower() and extension.startswith(".")
            assert extension not in seen, f"{extension} in {seen[extension]} and {category}"
            seen[extension] = category


def test_category_names_match_required_structure():
    assert all_category_names() == [
        "Images", "Videos", "Documents", "Code", "Archives", "Others",
    ]
