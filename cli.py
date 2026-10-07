"""Command-line interface. The only module that prints to the screen."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import List, Optional, Sequence

from . import __version__
from .analyzer import category_stats, extension_stats, find_large_files, total_size
from .classifier import all_category_names
from .config import DEFAULT_LARGE_FILE_BYTES, STATE_DIR_NAME
from .duplicates import find_duplicates
from .journal import JournalError
from .logger import close_logging, setup_logging
from .organizer import organize_directory
from .scanner import scan
from .search import SearchCriteria, search
from .undo import undo_last_run
from .utils import format_size, format_timestamp, parse_date, parse_size


# ----------------------------------------------------------------- helpers

def _size_arg(text: str) -> int:
    try:
        return parse_size(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


def _date_arg(text: str) -> float:
    try:
        return parse_date(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


def _rel(path: Path, root: Path) -> str:
    try:
        return Path(path).relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _table(headers: Sequence[str], rows: Sequence[Sequence[str]], right: Sequence[int] = ()) -> str:
    """Render a simple aligned text table. ``right`` lists right-aligned columns."""
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt(cells: Sequence[str]) -> str:
        parts = [
            cell.rjust(widths[i]) if i in right else cell.ljust(widths[i])
            for i, cell in enumerate(cells)
        ]
        return "  " + "  ".join(parts).rstrip()

    lines = [fmt(headers), "  " + "  ".join("-" * w for w in widths)]
    lines.extend(fmt(row) for row in rows)
    return "\n".join(lines)


def _scan_all(root: Path, args: argparse.Namespace):
    return list(scan(root, recursive=not args.no_recursive))


# --------------------------------------------------------------- commands

def cmd_organize(args: argparse.Namespace, root: Path) -> int:
    result = organize_directory(root, recursive=args.recursive, dry_run=args.dry_run)

    if not result.moved and not result.failed:
        print("Nothing to organize: everything is already in place.")
        return 0

    if args.dry_run:
        print(f"DRY RUN: no files will be changed. Planned moves ({len(result.moved)}):\n")
        for move in result.moved:
            print(f"  {_rel(move.source, root)}  ->  {_rel(move.destination, root)}")
        print()

    counts = Counter(move.category for move in result.moved)
    rows = [[name, str(counts[name])] for name in all_category_names() if counts[name]]
    verb = "Would move" if args.dry_run else "Moved"
    print(f"{verb} {len(result.moved)} file(s):")
    print(_table(["Category", "Files"], rows, right=[1]))

    if result.failed:
        print(f"\n{len(result.failed)} file(s) could not be moved:")
        for move, reason in result.failed:
            print(f"  {_rel(move.source, root)}: {reason}")

    if args.dry_run:
        print("\nRun again without --dry-run to apply these moves.")
    elif result.run_id:
        print(f"\nRun id: {result.run_id}")
        print(f"To reverse it:  python3 -m smart_file_manager undo {root}")
    return 1 if result.failed else 0


def cmd_duplicates(args: argparse.Namespace, root: Path) -> int:
    records = _scan_all(root, args)
    groups = find_duplicates(records, min_size=args.min_size)
    print(f"Scanned {len(records)} file(s).")

    if not groups:
        print("No duplicates found.")
        return 0

    for number, group in enumerate(groups, start=1):
        print(
            f"\nGroup {number}: {len(group.files)} identical files, "
            f"{format_size(group.size)} each  (sha256 {group.hash[:12]}...)"
        )
        for record in group.files:
            print(f"  {_rel(record.path, root)}")

    wasted = sum(group.wasted_bytes for group in groups)
    extra = sum(len(group.files) - 1 for group in groups)
    print(
        f"\n{len(groups)} duplicate group(s); {extra} redundant file(s) "
        f"waste {format_size(wasted)}."
    )
    return 0


def cmd_large(args: argparse.Namespace, root: Path) -> int:
    records = _scan_all(root, args)
    large = find_large_files(records, args.threshold)
    print(f"Scanned {len(records)} file(s). Threshold: {format_size(args.threshold)}.")

    if not large:
        print("No files at or above the threshold.")
        return 0

    shown = large[: args.top]
    rows = [
        [format_size(r.size), format_timestamp(r.modified), _rel(r.path, root)] for r in shown
    ]
    print()
    print(_table(["Size", "Modified", "Path"], rows, right=[0]))
    if len(large) > len(shown):
        print(f"\n...and {len(large) - len(shown)} more (use --top to show more).")
    print(f"\n{len(large)} large file(s), {format_size(total_size(large))} in total.")
    return 0


def cmd_analyze(args: argparse.Namespace, root: Path) -> int:
    records = _scan_all(root, args)
    if not records:
        print("No files found.")
        return 0

    grand_total = total_size(records)
    print(f"{len(records)} file(s), {format_size(grand_total)} in total.\n")

    def percent(size: int) -> str:
        return f"{(size / grand_total * 100):.1f}%" if grand_total else "0.0%"

    print("By category:")
    rows = [[s.name, str(s.count), format_size(s.total_size), percent(s.total_size)]
            for s in category_stats(records)]
    print(_table(["Category", "Files", "Size", "Share"], rows, right=[1, 2, 3]))

    ext_stats = extension_stats(records)
    print("\nBy extension:")
    rows = [[s.name, str(s.count), format_size(s.total_size), percent(s.total_size)]
            for s in ext_stats[: args.top]]
    print(_table(["Extension", "Files", "Size", "Share"], rows, right=[1, 2, 3]))
    if len(ext_stats) > args.top:
        print(f"\n...and {len(ext_stats) - args.top} more extension(s) (use --top to show more).")
    return 0


def cmd_search(args: argparse.Namespace, root: Path) -> int:
    criteria = SearchCriteria(
        name=args.name,
        extensions=args.ext,
        category=args.category,
        min_size=args.min_size,
        max_size=args.max_size,
        modified_after=args.after,
        modified_before=args.before,
    )
    records = _scan_all(root, args)
    found = search(records, criteria)

    if not found:
        print(f"No matches among {len(records)} file(s).")
        return 0

    rows = [[format_size(r.size), format_timestamp(r.modified), _rel(r.path, root)] for r in found]
    print(_table(["Size", "Modified", "Path"], rows, right=[0]))
    print(f"\n{len(found)} match(es) out of {len(records)} file(s).")
    return 0


def cmd_undo(args: argparse.Namespace, root: Path) -> int:
    result = undo_last_run(root, dry_run=args.dry_run)
    if result is None:
        print("Nothing to undo.")
        return 0

    verb = "Would restore" if args.dry_run else "Restored"
    print(f"Run {result.run_id}: {verb} {len(result.restored)} file(s).")
    if args.dry_run:
        for move in result.restored:
            print(f"  {move['destination']}  ->  {move['source']}")
    if result.failed:
        print(f"\n{len(result.failed)} file(s) could not be restored:")
        for move, reason in result.failed:
            print(f"  {move['destination']}: {reason}")
        return 1
    return 0


COMMANDS = {
    "organize": cmd_organize,
    "duplicates": cmd_duplicates,
    "large": cmd_large,
    "analyze": cmd_analyze,
    "search": cmd_search,
    "undo": cmd_undo,
}


# ----------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("path", type=Path, help="folder to work on, e.g. ~/Downloads")
    common.add_argument("-v", "--verbose", action="store_true",
                        help="show detailed progress messages")

    scan_opts = argparse.ArgumentParser(add_help=False)
    scan_opts.add_argument("--no-recursive", action="store_true",
                           help="only look at files directly inside the folder")

    parser = argparse.ArgumentParser(
        prog="smart_file_manager",
        description="Organize, deduplicate, analyze and search your files.",
        epilog="Tip: preview any change first with:  organize PATH --dry-run",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True, metavar="command")

    p = sub.add_parser("organize", parents=[common], help="sort files into category folders")
    p.add_argument("--dry-run", action="store_true", help="show what would happen, change nothing")
    p.add_argument("-r", "--recursive", action="store_true",
                   help="also organize files inside sub-folders (default: top level only)")

    p = sub.add_parser("duplicates", parents=[common, scan_opts],
                       help="find identical files using size + hash")
    p.add_argument("--min-size", type=_size_arg, default=1, metavar="SIZE",
                   help="ignore files smaller than SIZE, e.g. 10KB (default: 1 byte)")

    p = sub.add_parser("large", parents=[common, scan_opts], help="list the biggest files")
    p.add_argument("--threshold", type=_size_arg, default=DEFAULT_LARGE_FILE_BYTES, metavar="SIZE",
                   help="report files at least this big (default: 100MB)")
    p.add_argument("--top", type=int, default=20, metavar="N", help="show at most N files (default: 20)")

    p = sub.add_parser("analyze", parents=[common, scan_opts],
                       help="statistics by category and extension")
    p.add_argument("--top", type=int, default=15, metavar="N",
                   help="show at most N extensions (default: 15)")

    p = sub.add_parser("search", parents=[common, scan_opts], help="find files by name, type, size or date")
    p.add_argument("--name", help='text or glob pattern, e.g. invoice or "report*.pdf"')
    p.add_argument("--ext", nargs="+", metavar="EXT", help="one or more extensions, e.g. py txt")
    p.add_argument("--category", type=lambda s: s.capitalize(), choices=all_category_names(),
                   help="restrict to one category")
    p.add_argument("--min-size", type=_size_arg, metavar="SIZE", help="at least this big")
    p.add_argument("--max-size", type=_size_arg, metavar="SIZE", help="at most this big")
    p.add_argument("--after", type=_date_arg, metavar="YYYY-MM-DD", help="modified on or after")
    p.add_argument("--before", type=_date_arg, metavar="YYYY-MM-DD", help="modified before")

    p = sub.add_parser("undo", parents=[common], help="reverse the most recent organize run")
    p.add_argument("--dry-run", action="store_true", help="show what would be restored")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    root = args.path.expanduser().resolve()
    if not root.is_dir():
        print(f"Error: {args.path} is not a folder.", file=sys.stderr)
        return 2

    changes_files = args.command in {"organize", "undo"} and not args.dry_run
    setup_logging(
        log_dir=root / STATE_DIR_NAME if changes_files else None,
        verbose=args.verbose,
    )
    try:
        return COMMANDS[args.command](args, root)
    except JournalError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    finally:
        close_logging()
