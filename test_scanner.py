import os

import pytest

from smart_file_manager.scanner import scan


def names(records):
    return {record.name for record in records}


def test_scan_top_level_skips_hidden_files(downloads):
    found = names(scan(downloads, recursive=False))
    assert found == {"photo.JPG", "clip.mp4", "report.pdf", "script.py",
                     "bundle.zip", "mystery.xyz", "noext"}


def test_record_fields(downloads):
    record = next(r for r in scan(downloads) if r.name == "photo.JPG")
    assert record.extension == ".jpg"  # lowercased
    assert record.size == len(b"image-bytes")
    assert record.category is None and record.hash is None


def test_file_without_extension(downloads):
    record = next(r for r in scan(downloads) if r.name == "noext")
    assert record.extension == ""


def test_non_recursive_ignores_subfolders(downloads):
    sub = downloads / "sub"
    sub.mkdir()
    (sub / "nested.txt").write_text("x")
    assert "nested.txt" not in names(scan(downloads, recursive=False))


def test_recursive_finds_nested_files(downloads):
    deep = downloads / "a" / "b"
    deep.mkdir(parents=True)
    (deep / "deep.txt").write_text("x")
    assert "deep.txt" in names(scan(downloads, recursive=True))


def test_hidden_folders_are_skipped(downloads):
    state = downloads / ".sfm"
    state.mkdir()
    (state / "journal.json").write_text("[]")
    assert "journal.json" not in names(scan(downloads, recursive=True))


def test_exclude_top_level_only_applies_to_root(downloads):
    (downloads / "Images").mkdir()
    (downloads / "Images" / "organized.png").write_text("x")
    nested = downloads / "projects" / "Images"
    nested.mkdir(parents=True)
    (nested / "kept.png").write_text("x")

    found = names(scan(downloads, recursive=True, exclude_top_level={"Images"}))
    assert "organized.png" not in found
    assert "kept.png" in found


def test_symlinks_are_not_followed(downloads, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "elsewhere.txt").write_text("x")
    try:
        os.symlink(outside, downloads / "link_dir")
        os.symlink(downloads / "report.pdf", downloads / "link_file.pdf")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported here")

    found = names(scan(downloads, recursive=True))
    assert "elsewhere.txt" not in found
    assert "link_file.pdf" not in found


def test_empty_folder(tmp_path):
    assert list(scan(tmp_path)) == []
