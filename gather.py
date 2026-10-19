#!/usr/bin/env python3
"""
gather - collect files into a folder by file type, name pattern, and/or time.

Run `python gather.py --help` or see README.md for examples.
"""

import argparse
import fnmatch
import re
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path


# ---------- helpers ----------

def parse_dt(text, is_end=False):
    """Accepts 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM'. A date-only end includes the whole day."""
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(text, fmt)
            if is_end and fmt == "%Y-%m-%d":
                dt += timedelta(days=1) - timedelta(seconds=1)
            return dt
        except ValueError:
            pass
    sys.exit(f"Could not read date '{text}'. Use YYYY-MM-DD or 'YYYY-MM-DD HH:MM'.")


def file_time(path, by):
    st = path.stat()
    if by == "modified":
        return datetime.fromtimestamp(st.st_mtime)
    # "created": birthtime on macOS, ctime on Windows (creation time),
    # falls back to modified time on Linux where creation time isn't stored.
    created = getattr(st, "st_birthtime", None)
    if created is None:
        created = st.st_ctime if sys.platform == "win32" else st.st_mtime
    return datetime.fromtimestamp(created)


def compile_patterns(regexes, globs, case_sensitive, label):
    """Turn regex and glob strings into a list of compiled regexes."""
    flags = 0 if case_sensitive else re.IGNORECASE
    compiled = []
    for r in regexes or []:
        try:
            compiled.append(re.compile(r, flags))
        except re.error as e:
            sys.exit(f"Invalid regex for {label} '{r}': {e}")
    for g in globs or []:
        compiled.append(re.compile(fnmatch.translate(g), flags))
    return compiled


def unique_target(dest_dir, name):
    """Avoid overwriting: report.pdf -> report (1).pdf -> report (2).pdf"""
    target = dest_dir / name
    stem, suffix = Path(name).stem, Path(name).suffix
    i = 1
    while target.exists():
        target = dest_dir / f"{stem} ({i}){suffix}"
        i += 1
    return target


# ---------- main ----------

def build_parser():
    p = argparse.ArgumentParser(
        prog="gather",
        description="Collect files into a folder by file type, name pattern, and/or time interval. "
                    "Different filters are combined with AND; multiple values for the same filter are combined with OR.",
    )
    p.add_argument("dest", help="Folder to put the files in. A plain name is created inside --source; "
                                "an absolute path is used as-is.")
    p.add_argument("-s", "--source", default=".", help="Folder to scan (default: current directory)")
    p.add_argument("-r", "--recursive", action="store_true", help="Also scan subfolders")

    f = p.add_argument_group("filters (give at least one)")
    f.add_argument("-e", "--ext", nargs="+", metavar="EXT",
                   help="File extensions, e.g. pdf docx pptx (dot optional, case-insensitive)")
    f.add_argument("-n", "--name", action="append", metavar="REGEX",
                   help="Regex searched in the file name, e.g. 'CMSC' or '^lab\\d+'. Can be repeated.")
    f.add_argument("-g", "--glob", action="append", metavar="PATTERN",
                   help="Shell-style pattern on the file name, e.g. '*CMSC*'. Can be repeated.")
    f.add_argument("-x", "--exclude", action="append", metavar="REGEX",
                   help="Skip files whose name matches this regex. Can be repeated.")
    f.add_argument("--start", help="Earliest time (YYYY-MM-DD or 'YYYY-MM-DD HH:MM')")
    f.add_argument("--end", help="Latest time (inclusive; a date-only value covers the whole day)")
    f.add_argument("--by", choices=["modified", "created"], default="modified",
                   help="Which timestamp --start/--end use (default: modified)")
    f.add_argument("-c", "--case-sensitive", action="store_true",
                   help="Make --name/--glob/--exclude case-sensitive (default: case-insensitive)")

    a = p.add_argument_group("actions")
    a.add_argument("--copy", action="store_true", help="Copy instead of move")
    a.add_argument("-d", "--dry-run", action="store_true", help="Show what would happen without changing anything")
    return p


def main():
    args = build_parser().parse_args()

    if not (args.ext or args.name or args.glob or args.start or args.end):
        sys.exit("Give at least one filter (--ext, --name, --glob, --start, --end) "
                 "so the tool doesn't grab every file.")

    start = parse_dt(args.start) if args.start else None
    end = parse_dt(args.end, is_end=True) if args.end else None
    if start and end and start > end:
        sys.exit("--start must be earlier than --end.")

    source = Path(args.source).expanduser().resolve()
    if not source.is_dir():
        sys.exit(f"Source folder not found: {source}")

    dest_arg = Path(args.dest).expanduser()
    dest_dir = (dest_arg if dest_arg.is_absolute() else source / dest_arg).resolve()

    exts = {e.lower().lstrip(".") for e in args.ext} if args.ext else None
    name_pats = compile_patterns(args.name, args.glob, args.case_sensitive, "--name")
    exclude_pats = compile_patterns(args.exclude, None, args.case_sensitive, "--exclude")

    candidates = source.rglob("*") if args.recursive else source.iterdir()

    matches = []
    for f in candidates:
        if not f.is_file():
            continue
        if dest_dir == f.parent or dest_dir in f.parents:   # never re-process the destination
            continue
        if exts is not None and f.suffix.lower().lstrip(".") not in exts:
            continue
        if name_pats and not any(p.search(f.name) for p in name_pats):
            continue
        if exclude_pats and any(p.search(f.name) for p in exclude_pats):
            continue
        if start or end:
            t = file_time(f, args.by)
            if (start and t < start) or (end and t > end):
                continue
        matches.append(f)

    if not matches:
        print("No files matched.")
        return

    verb = "copy" if args.copy else "move"
    if not args.dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)

    for f in sorted(matches, key=lambda x: file_time(x, args.by)):
        stamp = file_time(f, args.by).strftime("%Y-%m-%d %H:%M")
        shown = f.relative_to(source) if f.is_relative_to(source) else f
        if args.dry_run:
            print(f"[dry run] would {verb}  {stamp}  {shown}")
        else:
            target = unique_target(dest_dir, f.name)
            (shutil.copy2 if args.copy else shutil.move)(str(f), str(target))
            print(f"{verb:<4}  {stamp}  {shown} -> {target.name}")

    done = f"would {verb}" if args.dry_run else ("copied" if args.copy else "moved")
    print(f"\n{len(matches)} file(s) {done} to {dest_dir}")


if __name__ == "__main__":
    main()
