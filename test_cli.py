import os

import pytest

from smart_file_manager.cli import main


def run(capsys, *argv):
    code = main([str(a) for a in argv])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_organize_dry_run(capsys, downloads):
    code, out, _ = run(capsys, "organize", downloads, "--dry-run")
    assert code == 0
    assert "DRY RUN" in out and "Would move 7 file(s)" in out
    assert (downloads / "report.pdf").exists()  # nothing moved
    assert not (downloads / ".sfm").exists()  # dry run writes no state either


def test_organize_then_undo(capsys, downloads):
    code, out, _ = run(capsys, "organize", downloads)
    assert code == 0 and "Moved 7 file(s)" in out and "Run id:" in out
    assert (downloads / "Documents" / "report.pdf").exists()

    code, out, _ = run(capsys, "undo", downloads)
    assert code == 0 and "Restored 7 file(s)" in out
    assert (downloads / "report.pdf").exists()


def test_organize_writes_log_file(capsys, downloads):
    run(capsys, "organize", downloads)
    log = (downloads / ".sfm" / "sfm.log").read_text()
    assert "Moved" in log and "report.pdf" in log


def test_organize_nothing_to_do(capsys, tmp_path):
    code, out, _ = run(capsys, "organize", tmp_path)
    assert code == 0 and "Nothing to organize" in out


def test_undo_nothing(capsys, downloads):
    code, out, _ = run(capsys, "undo", downloads)
    assert code == 0 and "Nothing to undo" in out


def test_invalid_path(capsys, tmp_path):
    code, _, err = run(capsys, "organize", tmp_path / "missing")
    assert code == 2 and "not a folder" in err


def test_duplicates_command(capsys, downloads):
    (downloads / "copy.pdf").write_bytes(b"pdf-bytes")
    code, out, _ = run(capsys, "duplicates", downloads)
    assert code == 0
    assert "Group 1" in out and "report.pdf" in out and "copy.pdf" in out
    assert "1 duplicate group(s)" in out


def test_duplicates_none(capsys, downloads):
    code, out, _ = run(capsys, "duplicates", downloads)
    assert code == 0 and "No duplicates found" in out


def test_large_command(capsys, downloads):
    (downloads / "huge.bin").write_bytes(b"0" * 5000)
    code, out, _ = run(capsys, "large", downloads, "--threshold", "1KB")
    assert code == 0 and "huge.bin" in out and "report.pdf" not in out


def test_large_none(capsys, downloads):
    code, out, _ = run(capsys, "large", downloads)
    assert code == 0 and "No files at or above" in out


def test_analyze_command(capsys, downloads):
    code, out, _ = run(capsys, "analyze", downloads)
    assert code == 0
    assert "By category:" in out and "By extension:" in out
    assert ".pdf" in out and "(none)" in out and "7 file(s)" in out


def test_search_command(capsys, downloads):
    code, out, _ = run(capsys, "search", downloads, "--ext", "py", "pdf")
    assert code == 0
    assert "script.py" in out and "report.pdf" in out and "clip.mp4" not in out
    assert "2 match(es)" in out


def test_search_by_name_and_category(capsys, downloads):
    code, out, _ = run(capsys, "search", downloads, "--name", "REP", "--category", "documents")
    assert code == 0 and "report.pdf" in out and "1 match(es)" in out


def test_search_by_date(capsys, downloads):
    old = downloads / "report.pdf"
    os.utime(old, (946684800, 946684800))  # 2000-01-01
    code, out, _ = run(capsys, "search", downloads, "--before", "2010-01-01")
    assert code == 0 and "report.pdf" in out and "1 match(es)" in out


def test_search_no_match(capsys, downloads):
    code, out, _ = run(capsys, "search", downloads, "--name", "zzz")
    assert code == 0 and "No matches" in out


def test_search_sees_organized_files(capsys, downloads):
    run(capsys, "organize", downloads)
    code, out, _ = run(capsys, "search", downloads, "--ext", "pdf")
    assert "Documents/report.pdf" in out


def test_bad_size_argument_is_rejected(capsys, downloads):
    with pytest.raises(SystemExit) as exc:
        main(["large", str(downloads), "--threshold", "lots"])
    assert exc.value.code == 2


def test_missing_command_is_rejected(capsys):
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2
