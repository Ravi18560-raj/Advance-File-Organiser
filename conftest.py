import pytest

from smart_file_manager.logger import close_logging


@pytest.fixture(autouse=True)
def _release_log_files():
    """Make sure no test leaves a log file handle open."""
    yield
    close_logging()


@pytest.fixture
def downloads(tmp_path):
    """A small, messy Downloads folder with one file per category."""
    root = tmp_path / "Downloads"
    root.mkdir()
    (root / "photo.JPG").write_bytes(b"image-bytes")
    (root / "clip.mp4").write_bytes(b"video-bytes")
    (root / "report.pdf").write_bytes(b"pdf-bytes")
    (root / "script.py").write_text("print('hi')\n")
    (root / "bundle.zip").write_bytes(b"zip-bytes")
    (root / "mystery.xyz").write_bytes(b"???")
    (root / "noext").write_bytes(b"data")
    (root / ".hidden").write_text("secret")
    return root
