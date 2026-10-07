"""Central configuration: category definitions and tunable constants.

Everything a user might reasonably want to tweak lives here, so the rest of
the code never contains "magic" extension lists or thresholds.
"""

from __future__ import annotations

# Category name -> set of lowercase extensions (with the leading dot).
# Insertion order matters only for display; lookups use a reverse map.
CATEGORIES: dict[str, frozenset[str]] = {
    "Images": frozenset({
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp",
        ".svg", ".heic", ".ico", ".raw", ".psd",
    }),
    "Videos": frozenset({
        ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v",
        ".mpeg", ".mpg", ".3gp",
    }),
    "Documents": frozenset({
        ".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx",
        ".ppt", ".pptx", ".csv", ".md", ".epub", ".pages", ".numbers", ".key",
    }),
    "Code": frozenset({
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h",
        ".hpp", ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".html",
        ".css", ".json", ".xml", ".yaml", ".yml", ".sh", ".sql", ".ipynb",
    }),
    "Archives": frozenset({
        ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".tgz", ".iso",
        ".dmg",
    }),
}

# Anything that matches no category above ends up here.
OTHERS = "Others"

# Files at or above this size are reported by the `large` command by default.
DEFAULT_LARGE_FILE_BYTES = 100 * 1024 * 1024  # 100 MB

# Hashing settings.
HASH_ALGORITHM = "sha256"
HASH_CHUNK_SIZE = 1024 * 1024  # read files 1 MB at a time
PARTIAL_HASH_BYTES = 64 * 1024  # "quick check" hash covers the first 64 KB

# Hidden state folder created inside the organized directory.
STATE_DIR_NAME = ".sfm"
JOURNAL_FILE_NAME = "journal.json"
LOG_FILE_NAME = "sfm.log"
