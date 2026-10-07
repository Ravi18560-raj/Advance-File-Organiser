import json

import pytest

from smart_file_manager.journal import JournalError, journal_path, load_runs
from smart_file_manager.organizer import organize_directory
from smart_file_manager.undo import undo_last_run


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob("*") if p.is_file() and ".sfm" not in p.parts}


def test_undo_restores_everything(downloads):
    before = snapshot(downloads)
    organize_directory(downloads)

    result = undo_last_run(downloads)

    assert len(result.restored) == 7 and result.failed == []
    assert snapshot(downloads) == before


def test_undo_removes_empty_category_folders_and_clears_journal(downloads):
    organize_directory(downloads)
    undo_last_run(downloads)
    for name in ["Images", "Videos", "Documents", "Code", "Archives", "Others"]:
        assert not (downloads / name).exists()
    assert load_runs(downloads) == []


def test_undo_with_nothing_to_undo(downloads):
    assert undo_last_run(downloads) is None


def test_undo_only_reverses_the_latest_run(downloads):
    organize_directory(downloads)
    (downloads / "late.txt").write_text("new arrival")
    organize_directory(downloads)

    undo_last_run(downloads)

    assert (downloads / "late.txt").exists()  # second run reversed
    assert (downloads / "Images" / "photo.JPG").exists()  # first run intact
    assert len(load_runs(downloads)) == 1


def test_undo_restores_nested_files_to_original_folder(downloads):
    (downloads / "sub").mkdir()
    (downloads / "sub" / "nested.txt").write_text("x")
    organize_directory(downloads, recursive=True)
    undo_last_run(downloads)
    assert (downloads / "sub" / "nested.txt").exists()


def test_undo_dry_run_changes_nothing(downloads):
    organize_directory(downloads)
    organized = snapshot(downloads)

    result = undo_last_run(downloads, dry_run=True)

    assert len(result.restored) == 7
    assert snapshot(downloads) == organized
    assert len(load_runs(downloads)) == 1


def test_conflict_keeps_move_in_journal_for_retry(downloads):
    organize_directory(downloads)
    (downloads / "photo.JPG").write_text("someone put a new file here")

    result = undo_last_run(downloads)

    assert [m["source"] for m, _ in result.failed] == ["photo.JPG"]
    assert (downloads / "Images" / "photo.JPG").exists()  # not overwritten or lost
    assert (downloads / "photo.JPG").read_text() == "someone put a new file here"
    remaining = load_runs(downloads)[0]["moves"]
    assert [m["source"] for m in remaining] == ["photo.JPG"]

    # Resolve the conflict, then retry.
    (downloads / "photo.JPG").unlink()
    retry = undo_last_run(downloads)
    assert retry.failed == [] and (downloads / "photo.JPG").read_bytes() == b"image-bytes"
    assert load_runs(downloads) == []


def test_missing_organized_file_is_reported_and_dropped(downloads):
    organize_directory(downloads)
    (downloads / "Documents" / "report.pdf").unlink()

    result = undo_last_run(downloads)

    assert [m["source"] for m, _ in result.failed] == ["report.pdf"]
    assert len(result.restored) == 6
    assert load_runs(downloads) == []  # retrying could never succeed


def test_corrupt_journal_raises_clear_error(downloads):
    organize_directory(downloads)
    journal_path(downloads).write_text("{ not json")
    with pytest.raises(JournalError):
        undo_last_run(downloads)


def test_journal_survives_folder_rename(downloads, tmp_path):
    organize_directory(downloads)
    renamed = tmp_path / "Renamed"
    downloads.rename(renamed)
    result = undo_last_run(renamed)
    assert len(result.restored) == 7 and (renamed / "report.pdf").exists()


def test_journal_is_valid_json(downloads):
    organize_directory(downloads)
    data = json.loads(journal_path(downloads).read_text())
    assert isinstance(data, list) and data[0]["moves"]
