# Smart File Management System

A command-line tool that organizes a messy folder (like `Downloads/`) and helps you
understand it: duplicate detection, large-file detection, extension analysis, search,
and a safe **undo**. Standard library only, no dependencies.

```
Downloads/
├── Images/       .jpg .png .gif .webp ...
├── Videos/       .mp4 .mkv .mov ...
├── Documents/    .pdf .docx .txt .xlsx ...
├── Code/         .py .js .java .json ...
├── Archives/     .zip .rar .7z .tar.gz ...
└── Others/       everything else
```

## Quick start

Requires Python 3.9+.

```bash
python3 -m smart_file_manager organize ~/Downloads --dry-run   # preview first
python3 -m smart_file_manager organize ~/Downloads             # do it
python3 -m smart_file_manager undo ~/Downloads                 # changed your mind
```

Optional: `pip install -e .` gives you a short command, `sfm`, instead of
`python3 -m smart_file_manager`.

## Commands

| Command | What it does |
|---|---|
| `organize PATH [--dry-run] [-r]` | Sort files into the six category folders. Top level only unless `-r`. |
| `undo PATH [--dry-run]` | Reverse the most recent organize run. |
| `duplicates PATH [--min-size SIZE]` | Find byte-identical files and show wasted space. |
| `large PATH [--threshold SIZE] [--top N]` | List files above a size (default 100MB). |
| `analyze PATH [--top N]` | Count and size per category and per extension. |
| `search PATH [filters]` | Find files by name/glob, extension, category, size, date. |

Common options: `-v` (verbose), `--no-recursive` (for read-only commands),
sizes like `500`, `10KB`, `1.5GB`, dates as `YYYY-MM-DD`.

```bash
sfm duplicates ~/Downloads --min-size 10KB
sfm large ~/Downloads --threshold 500MB
sfm analyze ~/Downloads --top 10
sfm search ~/Downloads --name "invoice*" --ext pdf --after 2026-01-01
sfm search ~/Downloads --category Images --min-size 5MB
```

## How it works

```
scanner -> FileRecord list -> classifier -> organizer (plan -> execute) -> journal
                                  |                                          |
                          analyzer / search / duplicates                    undo
```

| Module | Responsibility |
|---|---|
| `config.py` | Category -> extension map, thresholds. Edit this to customize. |
| `models.py` | `FileRecord`, `MovePlan` dataclasses shared by everything. |
| `scanner.py` | Walks a folder, yields `FileRecord`s. Never modifies anything. |
| `classifier.py` | Extension -> category (O(1) reverse lookup). |
| `organizer.py` | Builds a move **plan**, then executes it. Only module that moves files. |
| `hasher.py` | SHA-256 in 1 MB chunks, so huge files never fill memory. |
| `duplicates.py` | Three-stage filter: size, then quick hash, then full hash. |
| `analyzer.py` | Extension/category statistics and large-file detection. |
| `search.py` | Combines filters with AND. |
| `journal.py` | JSON record of every move, written atomically. |
| `undo.py` | Replays the journal in reverse. |
| `logger.py` | Console warnings plus a rotating log file. |
| `cli.py` | argparse. The only module that prints. |

### Design decisions worth knowing (good interview material)

- **Plan, then execute.** `--dry-run` runs the exact same planning code and just skips
  execution, so the preview cannot disagree with reality.
- **Duplicate detection avoids hashing whenever possible.** Different sizes cannot be
  identical, so only same-size files are compared; the first 64 KB is hashed next, and
  a full hash is computed only for files that still match.
- **Nothing is ever overwritten.** Name clashes become `report (1).pdf`. Undo refuses to
  overwrite a file that now sits at the original location and keeps that move in the
  journal so you can resolve it and retry.
- **The journal stores relative paths**, so undo still works if you rename or move the folder.
- **Journal writes are atomic** (write to a temp file, then `os.replace`), so a crash can't
  corrupt it. Files moved before an interruption are still journaled.
- **Safe scanning.** Hidden files/folders and symlinks are skipped; unreadable files are
  logged and skipped instead of crashing the run.

## State and logs

Created inside the organized folder in a hidden `.sfm/` directory:

- `journal.json`: the undo history
- `sfm.log`: timestamped log of every move and restore (rotating, max ~4 MB)

## Tests

```bash
pip install pytest
python3 -m pytest
```

118 tests cover every module plus the CLI end to end (organize -> undo round trips,
name collisions, undo conflicts, corrupt journals, failure handling).

## Ideas for extending it

- Move or delete duplicates interactively (`duplicates --delete`), always keeping one copy.
- Load categories from a user `config.json`.
- Organize by date (`Images/2026/10/`).
- Watch mode that organizes new downloads automatically.
