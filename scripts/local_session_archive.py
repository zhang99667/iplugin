#!/usr/bin/env python3
"""Local Codex / Claude session archive utility.

The tool copies JSONL session files into a local archive directory and keeps a
small append-only index. It does not upload data or require network access.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_ARCHIVE_ROOT = Path("~/.local/share/iplugin/session-archive")
DEFAULT_SOURCES = {
    "codex": [Path("~/.codex/sessions")],
    "claude": [Path("~/.claude/projects"), Path("~/.claude/sessions")],
}


@dataclass(frozen=True)
class SessionFile:
    source: str
    root: Path
    path: Path

    @property
    def session_id(self) -> str:
        return self.path.stem

    @property
    def relative_path(self) -> Path:
        return self.path.relative_to(self.root)


def expand(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def file_day(path: Path) -> str:
    timestamp = path.stat().st_mtime
    return dt.datetime.fromtimestamp(timestamp).strftime("%Y%m%d")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def archive_root(args: argparse.Namespace) -> Path:
    value = args.archive_root or os.environ.get("IPPLUGIN_SESSION_ARCHIVE_DIR") or DEFAULT_ARCHIVE_ROOT
    return expand(value)


def index_path(root: Path) -> Path:
    return root / "index.jsonl"


def load_index(root: Path) -> list[dict[str, Any]]:
    path = index_path(root)
    if not path.is_file():
        return []
    entries: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                entries.append(data)
    return entries


def latest_by_source_path(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for entry in entries:
        key = str(entry.get("source_path") or "")
        if key:
            latest[key] = entry
    return latest


def write_index_entry(root: Path, entry: dict[str, Any]) -> None:
    path = index_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True))
        handle.write("\n")


def selected_sources(source: str) -> dict[str, list[Path]]:
    if source == "all":
        return DEFAULT_SOURCES
    if source not in DEFAULT_SOURCES:
        raise SystemExit(f"unknown source: {source}")
    return {source: DEFAULT_SOURCES[source]}


def discover_sessions(source: str, extra_root: list[str] | None = None) -> list[SessionFile]:
    sessions: list[SessionFile] = []
    for source_name, roots in selected_sources(source).items():
        search_roots = list(roots)
        if extra_root:
            search_roots.extend(Path(item) for item in extra_root)
        for root in search_roots:
            expanded_root = expand(root)
            if not expanded_root.is_dir():
                continue
            for path in sorted(expanded_root.rglob("*.jsonl")):
                if path.is_file():
                    sessions.append(SessionFile(source_name, expanded_root, path.resolve()))
    return sessions


def archive_path(root: Path, session: SessionFile) -> Path:
    return root / "sessions" / session.source / file_day(session.path) / session.relative_path


def cmd_sync(args: argparse.Namespace) -> int:
    root = archive_root(args)
    root.mkdir(parents=True, exist_ok=True)
    index = load_index(root)
    latest = latest_by_source_path(index)
    sessions = discover_sessions(args.source, args.root)

    copied = 0
    skipped = 0
    for session in sessions:
        stat = session.path.stat()
        digest = sha256_file(session.path)
        source_path = session.path.as_posix()
        previous = latest.get(source_path)
        if previous and previous.get("sha256") == digest:
            skipped += 1
            continue

        target = archive_path(root, session)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(session.path, target)

        entry = {
            "archived_at": utc_now(),
            "archived_path": target.as_posix(),
            "mtime": int(stat.st_mtime),
            "relative_path": session.relative_path.as_posix(),
            "session_id": session.session_id,
            "sha256": digest,
            "size": stat.st_size,
            "source": session.source,
            "source_path": source_path,
        }
        write_index_entry(root, entry)
        latest[source_path] = entry
        copied += 1

    print(json.dumps({
        "archive_root": root.as_posix(),
        "copied": copied,
        "discovered": len(sessions),
        "skipped": skipped,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    interval = max(5, args.interval)
    print(f"Watching sessions every {interval}s. Archive root: {archive_root(args)}", flush=True)
    while True:
        cmd_sync(args)
        time.sleep(interval)


def recent_entries(root: Path) -> list[dict[str, Any]]:
    latest = latest_by_source_path(load_index(root))
    return sorted(latest.values(), key=lambda item: str(item.get("archived_at", "")), reverse=True)


def cmd_list(args: argparse.Namespace) -> int:
    root = archive_root(args)
    entries = recent_entries(root)
    if args.source != "all":
        entries = [entry for entry in entries if entry.get("source") == args.source]
    if args.limit > 0:
        entries = entries[: args.limit]

    if args.json:
        print(json.dumps(entries, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if not entries:
        print("No archived sessions found.")
        return 0

    for entry in entries:
        print(
            f"{entry.get('source', '-'):6} "
            f"{entry.get('session_id', '-'):36} "
            f"{entry.get('archived_at', '-')} "
            f"{entry.get('size', 0)} bytes"
        )
        print(f"  {entry.get('archived_path', '')}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = archive_root(args)
    sessions = discover_sessions(args.source, args.root)
    entries = recent_entries(root)
    by_source: dict[str, dict[str, int]] = {}
    for session in sessions:
        by_source.setdefault(session.source, {"source_files": 0, "archived_files": 0})
        by_source[session.source]["source_files"] += 1
    for entry in entries:
        source = str(entry.get("source") or "unknown")
        by_source.setdefault(source, {"source_files": 0, "archived_files": 0})
        by_source[source]["archived_files"] += 1

    print(json.dumps({
        "archive_root": root.as_posix(),
        "index_path": index_path(root).as_posix(),
        "sources": by_source,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def find_restore_entry(root: Path, args: argparse.Namespace) -> dict[str, Any] | None:
    entries = recent_entries(root)
    if args.path:
        wanted = expand(args.path).as_posix()
        for entry in entries:
            if expand(str(entry.get("archived_path", ""))).as_posix() == wanted:
                return entry
        return None
    if args.id:
        matches = [
            entry for entry in entries
            if args.id in str(entry.get("session_id", "")) or args.id in str(entry.get("archived_path", ""))
        ]
        if len(matches) > 1:
            print("Multiple sessions match; use a longer --id or --path:", file=sys.stderr)
            for entry in matches[:20]:
                print(f"  {entry.get('session_id')}  {entry.get('archived_path')}", file=sys.stderr)
            raise SystemExit(2)
        return matches[0] if matches else None
    raise SystemExit("restore requires --id or --path")


def cmd_restore(args: argparse.Namespace) -> int:
    root = archive_root(args)
    entry = find_restore_entry(root, args)
    if not entry:
        print("No matching archived session found.", file=sys.stderr)
        return 1

    source = Path(str(entry["archived_path"]))
    if not source.is_file():
        print(f"Archived file does not exist: {source}", file=sys.stderr)
        return 1

    if args.to_source:
        target = Path(str(entry["source_path"]))
    elif args.target:
        target = expand(args.target)
    else:
        target = root / "restored" / str(entry.get("source") or "unknown") / source.name

    if target.exists() and not args.overwrite:
        print(f"Refusing to overwrite existing file: {target}", file=sys.stderr)
        print("Pass --overwrite to replace it.", file=sys.stderr)
        return 1

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    print(json.dumps({
        "restored_from": source.as_posix(),
        "restored_to": target.as_posix(),
        "session_id": entry.get("session_id"),
        "source": entry.get("source"),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local Codex / Claude JSONL session archive")
    parser.add_argument("--archive-root", help="Archive directory; defaults to IPPLUGIN_SESSION_ARCHIVE_DIR or ~/.local/share/iplugin/session-archive")

    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_source_flags(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--source", choices=["all", "codex", "claude"], default="all")
        subparser.add_argument("--root", action="append", help="Extra source root to scan for *.jsonl files")

    sync = subparsers.add_parser("sync", help="Copy new or changed sessions into the local archive")
    add_source_flags(sync)
    sync.set_defaults(func=cmd_sync)

    watch = subparsers.add_parser("watch", help="Run sync repeatedly in the foreground")
    add_source_flags(watch)
    watch.add_argument("--interval", type=int, default=60, help="Seconds between sync runs; minimum 5")
    watch.set_defaults(func=cmd_watch)

    list_cmd = subparsers.add_parser("list", help="List archived sessions")
    list_cmd.add_argument("--source", choices=["all", "codex", "claude"], default="all")
    list_cmd.add_argument("--limit", type=int, default=20)
    list_cmd.add_argument("--json", action="store_true", help="Print JSON instead of a table")
    list_cmd.set_defaults(func=cmd_list)

    status = subparsers.add_parser("status", help="Show source and archive counts")
    add_source_flags(status)
    status.set_defaults(func=cmd_status)

    restore = subparsers.add_parser("restore", help="Restore an archived session file")
    restore.add_argument("--id", help="Session id or archived path substring")
    restore.add_argument("--path", help="Exact archived file path")
    restore.add_argument("--target", help="Restore to this path")
    restore.add_argument("--to-source", action="store_true", help="Restore to the original source path")
    restore.add_argument("--overwrite", action="store_true", help="Allow replacing an existing target")
    restore.set_defaults(func=cmd_restore)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
