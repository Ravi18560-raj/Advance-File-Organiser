from smart_file_manager.config import PARTIAL_HASH_BYTES
from smart_file_manager.duplicates import find_duplicates
from smart_file_manager.scanner import scan


def find(root, **kwargs):
    return find_duplicates(list(scan(root)), **kwargs)


def test_finds_identical_small_files(tmp_path):
    (tmp_path / "a.txt").write_bytes(b"same content")
    (tmp_path / "b.txt").write_bytes(b"same content")
    (tmp_path / "c.txt").write_bytes(b"different!!!")

    groups = find(tmp_path)

    assert len(groups) == 1
    assert [r.name for r in groups[0].files] == ["a.txt", "b.txt"]
    assert groups[0].size == len(b"same content")
    assert groups[0].files[0].hash == groups[0].hash


def test_same_size_different_content_is_not_duplicate(tmp_path):
    (tmp_path / "a").write_bytes(b"aaaa")
    (tmp_path / "b").write_bytes(b"bbbb")
    assert find(tmp_path) == []


def test_unique_files_produce_no_groups(tmp_path):
    (tmp_path / "a").write_bytes(b"1")
    (tmp_path / "b").write_bytes(b"22")
    assert find(tmp_path) == []


def test_duplicates_across_subfolders(tmp_path):
    (tmp_path / "x").mkdir()
    (tmp_path / "y").mkdir()
    (tmp_path / "x" / "one.bin").write_bytes(b"payload")
    (tmp_path / "y" / "two.bin").write_bytes(b"payload")
    assert len(find(tmp_path)) == 1


def test_empty_files_ignored_by_default(tmp_path):
    (tmp_path / "a").write_bytes(b"")
    (tmp_path / "b").write_bytes(b"")
    assert find(tmp_path) == []
    assert len(find(tmp_path, min_size=0)) == 1


def test_min_size_filter(tmp_path):
    (tmp_path / "a").write_bytes(b"tiny")
    (tmp_path / "b").write_bytes(b"tiny")
    assert find(tmp_path, min_size=100) == []


def test_large_files_with_identical_prefix_but_different_tail(tmp_path):
    prefix = b"p" * (PARTIAL_HASH_BYTES + 10)
    (tmp_path / "a").write_bytes(prefix + b"AAAA")
    (tmp_path / "b").write_bytes(prefix + b"BBBB")
    assert find(tmp_path) == []  # quick hash matches, full hash must reject


def test_large_identical_files_are_found(tmp_path):
    data = b"q" * (PARTIAL_HASH_BYTES * 3) + b"end"
    (tmp_path / "a").write_bytes(data)
    (tmp_path / "b").write_bytes(data)
    (tmp_path / "c").write_bytes(data)

    groups = find(tmp_path)

    assert len(groups) == 1
    assert len(groups[0].files) == 3
    assert groups[0].wasted_bytes == len(data) * 2


def test_groups_sorted_by_wasted_space(tmp_path):
    (tmp_path / "s1").write_bytes(b"small")
    (tmp_path / "s2").write_bytes(b"small")
    (tmp_path / "b1").write_bytes(b"b" * 5000)
    (tmp_path / "b2").write_bytes(b"b" * 5000)

    groups = find(tmp_path)

    assert [g.size for g in groups] == [5000, 5]


def test_multiple_independent_groups(tmp_path):
    for name, data in [("a1", b"AAA"), ("a2", b"AAA"), ("b1", b"BBB"), ("b2", b"BBB")]:
        (tmp_path / name).write_bytes(data)
    assert len(find(tmp_path)) == 2
