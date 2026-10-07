import pytest

from smart_file_manager.utils import format_size, parse_date, parse_size


@pytest.mark.parametrize("number, expected", [
    (0, "0 B"),
    (512, "512 B"),
    (1024, "1.0 KB"),
    (1536, "1.5 KB"),
    (5 * 1024 ** 2, "5.0 MB"),
    (3 * 1024 ** 3, "3.0 GB"),
    (2 * 1024 ** 5, "2048.0 TB"),
])
def test_format_size(number, expected):
    assert format_size(number) == expected


@pytest.mark.parametrize("text, expected", [
    ("500", 500),
    ("10KB", 10 * 1024),
    ("10 kb", 10 * 1024),
    ("1.5MB", int(1.5 * 1024 ** 2)),
    ("2g", 2 * 1024 ** 3),
    ("1TB", 1024 ** 4),
])
def test_parse_size(text, expected):
    assert parse_size(text) == expected


@pytest.mark.parametrize("text", ["", "abc", "10XB", "-5MB", "MB"])
def test_parse_size_rejects_garbage(text):
    with pytest.raises(ValueError):
        parse_size(text)


def test_parse_date():
    assert parse_date("2026-01-31") > parse_date("2026-01-30")


@pytest.mark.parametrize("text", ["31-01-2026", "2026/01/31", "yesterday"])
def test_parse_date_rejects_garbage(text):
    with pytest.raises(ValueError):
        parse_date(text)
