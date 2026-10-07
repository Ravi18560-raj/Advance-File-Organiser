import hashlib

from smart_file_manager.config import PARTIAL_HASH_BYTES
from smart_file_manager.hasher import hash_file, quick_hash


def test_matches_hashlib(tmp_path):
    path = tmp_path / "a.bin"
    path.write_bytes(b"hello")
    assert hash_file(path) == hashlib.sha256(b"hello").hexdigest()


def test_chunked_reading_gives_same_result(tmp_path):
    data = bytes(range(256)) * 5000  # ~1.3 MB
    path = tmp_path / "big.bin"
    path.write_bytes(data)
    assert hash_file(path, chunk_size=1000) == hashlib.sha256(data).hexdigest()


def test_empty_file(tmp_path):
    path = tmp_path / "empty"
    path.write_bytes(b"")
    assert hash_file(path) == hashlib.sha256(b"").hexdigest()


def test_max_bytes_hashes_only_the_prefix(tmp_path):
    path = tmp_path / "a.bin"
    path.write_bytes(b"abcdefghij")
    assert hash_file(path, max_bytes=4) == hashlib.sha256(b"abcd").hexdigest()
    assert hash_file(path, max_bytes=4, chunk_size=3) == hashlib.sha256(b"abcd").hexdigest()


def test_quick_hash_ignores_the_tail(tmp_path):
    prefix = b"x" * PARTIAL_HASH_BYTES
    a, b = tmp_path / "a", tmp_path / "b"
    a.write_bytes(prefix + b"tail-one")
    b.write_bytes(prefix + b"tail-two")
    assert quick_hash(a) == quick_hash(b)
    assert hash_file(a) != hash_file(b)


def test_different_content_different_hash(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.write_bytes(b"one")
    b.write_bytes(b"two")
    assert hash_file(a) != hash_file(b)
