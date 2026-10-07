import shutil

from smart_file_manager.journal import load_runs
from smart_file_manager.organizer import organize_directory, unique_destination


def listing(root):
    """Visible files only (hidden files and the .sfm state folder are ignored)."""
    return sorted(
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and not any(part.startswith(".") for part in p.relative_to(root).parts)
    )


def test_dry_run_changes_nothing(downloads):
    before = listing(downloads)
    result = organize_directory(downloads, dry_run=True)
    assert listing(downloads) == before
    assert result.dry_run and len(result.moved) == 7
    assert load_runs(downloads) == []  # nothing journaled either


def test_files_land_in_category_folders(downloads):
    organize_directory(downloads)
    assert listing(downloads) == [
        "Archives/bundle.zip",
        "Code/script.py",
        "Documents/report.pdf",
        "Images/photo.JPG",
        "Others/mystery.xyz",
        "Others/noext",
        "Videos/clip.mp4",
    ]
    assert (downloads / ".hidden").exists()  # hidden files are left alone


def test_second_run_is_a_no_op(downloads):
    organize_directory(downloads)
    second = organize_directory(downloads)
    assert second.moved == [] and second.failed == []
    assert len(load_runs(downloads)) == 1  # no empty run recorded


def test_name_collisions_get_numbered(downloads):
    organize_directory(downloads)
    (downloads / "report.pdf").write_bytes(b"a newer report")
    organize_directory(downloads)
    assert (downloads / "Documents" / "report.pdf").read_bytes() == b"pdf-bytes"
    assert (downloads / "Documents" / "report (1).pdf").read_bytes() == b"a newer report"


def test_collisions_inside_one_run(tmp_path):
    root = tmp_path / "d"
    (root / "a").mkdir(parents=True)
    (root / "b").mkdir()
    (root / "a" / "same.txt").write_text("from a")
    (root / "b" / "same.txt").write_text("from b")

    organize_directory(root, recursive=True)

    assert sorted(p.name for p in (root / "Documents").iterdir()) == ["same (1).txt", "same.txt"]


def test_non_recursive_leaves_subfolders_alone(downloads):
    (downloads / "sub").mkdir()
    (downloads / "sub" / "nested.txt").write_text("x")
    organize_directory(downloads)
    assert (downloads / "sub" / "nested.txt").exists()


def test_recursive_organizes_nested_files(downloads):
    (downloads / "sub").mkdir()
    (downloads / "sub" / "nested.txt").write_text("x")
    organize_directory(downloads, recursive=True)
    assert (downloads / "Documents" / "nested.txt").exists()
    assert not (downloads / "sub" / "nested.txt").exists()


def test_recursive_does_not_touch_already_organized_files(downloads):
    organize_directory(downloads)
    result = organize_directory(downloads, recursive=True)
    assert result.moved == []


def test_run_is_journaled_with_relative_paths(downloads):
    result = organize_directory(downloads)
    runs = load_runs(downloads)
    assert len(runs) == 1 and runs[0]["id"] == result.run_id
    moves = {m["source"]: m["destination"] for m in runs[0]["moves"]}
    assert moves["photo.JPG"] == "Images/photo.JPG"


def test_file_named_like_a_category_is_just_organized(downloads):
    (downloads / "Images").write_text("a file, not a folder")
    organize_directory(downloads)
    assert (downloads / "Others" / "Images").exists()
    assert (downloads / "Images" / "photo.JPG").exists()


def test_failure_is_reported_and_other_files_still_move(downloads, monkeypatch):
    real_move = shutil.move

    def flaky_move(src, dst, *args, **kwargs):
        if src.endswith("photo.JPG"):
            raise PermissionError("simulated failure")
        return real_move(src, dst, *args, **kwargs)

    monkeypatch.setattr("smart_file_manager.organizer.shutil.move", flaky_move)
    result = organize_directory(downloads)
    assert [m.source.name for m, _ in result.failed] == ["photo.JPG"]
    assert (downloads / "Documents" / "report.pdf").exists()
    assert (downloads / "photo.JPG").exists()


def test_unique_destination_skips_taken_and_existing(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    taken = {str(tmp_path / "a (1).txt").lower()}
    assert unique_destination(tmp_path, "a.txt", taken) == tmp_path / "a (2).txt"
    assert unique_destination(tmp_path, "fresh.txt", taken) == tmp_path / "fresh.txt"
