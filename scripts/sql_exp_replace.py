#!/usr/bin/env python3
"""Deterministically replace experiment ids and event_day ranges in SQL.

The script intentionally handles only mechanical replacement. The calling
assistant should resolve ambiguous experiment mapping before invoking it.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


TOKEN_RE = re.compile(r"^[A-Za-z0-9_]+(?:-(?:0|dz))?$")
DATE_RE = re.compile(r"^\d{8}$")
SHORT_DATE_RE = re.compile(r"^\d{4}$")

EVENT_DAY_BETWEEN_RE = re.compile(
    r"(?i)(\bevent_day\b\s+between\s*)"
    r"(?P<q1>['\"]?)(?P<start>\d{8})(?P=q1)"
    r"(\s+and\s*)"
    r"(?P<q2>['\"]?)(?P<end>\d{8})(?P=q2)"
)


@dataclass(frozen=True)
class Replacement:
    old: str
    new: str


@dataclass
class ReplacementStats:
    date_ranges: int = 0
    experiment_counts: dict[str, int] | None = None

    def __post_init__(self) -> None:
        if self.experiment_counts is None:
            self.experiment_counts = {}


def parse_replacement(value: str) -> Replacement:
    if "=" not in value:
        raise argparse.ArgumentTypeError(f"mapping must use OLD=NEW format: {value!r}")
    old, new = (part.strip() for part in value.split("=", 1))
    if not old or not new:
        raise argparse.ArgumentTypeError(f"mapping must not contain empty sides: {value!r}")
    if not TOKEN_RE.fullmatch(old):
        raise argparse.ArgumentTypeError(f"unsupported old experiment token: {old!r}")
    if not TOKEN_RE.fullmatch(new):
        raise argparse.ArgumentTypeError(f"unsupported new experiment token: {new!r}")
    return Replacement(old=old, new=new)


def normalize_date(value: str, year: str | None) -> str:
    value = value.strip()
    if DATE_RE.fullmatch(value):
        return value
    if SHORT_DATE_RE.fullmatch(value):
        if not year:
            raise ValueError(f"date {value!r} is MMDD; provide --year to expand it")
        return f"{year}{value}"
    raise ValueError(f"date must be YYYYMMDD or MMDD: {value!r}")


def replace_event_day_between(sql: str, start: str, end: str) -> tuple[str, int]:
    def repl(match: re.Match[str]) -> str:
        return (
            f"{match.group(1)}"
            f"{match.group('q1')}{start}{match.group('q1')}"
            f"{match.group(4)}"
            f"{match.group('q2')}{end}{match.group('q2')}"
        )

    return EVENT_DAY_BETWEEN_RE.subn(repl, sql)


def token_pattern(token: str) -> re.Pattern[str]:
    escaped = re.escape(token)
    if "-" in token:
        return re.compile(rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])")
    return re.compile(rf"(?<![A-Za-z0-9_]){escaped}(?P<suffix>-(?:0|dz))?(?![A-Za-z0-9_])")


def replace_experiment(sql: str, replacement: Replacement) -> tuple[str, int]:
    pattern = token_pattern(replacement.old)

    def repl(match: re.Match[str]) -> str:
        if "-" in replacement.old or "-" in replacement.new:
            return replacement.new
        return f"{replacement.new}{match.group('suffix') or ''}"

    return pattern.subn(repl, sql)


def transform_sql(
    sql: str,
    replacements: list[Replacement],
    date_start: str | None,
    date_end: str | None,
) -> tuple[str, ReplacementStats]:
    stats = ReplacementStats()
    output = sql

    for replacement in replacements:
        output, count = replace_experiment(output, replacement)
        assert stats.experiment_counts is not None
        stats.experiment_counts[f"{replacement.old}={replacement.new}"] = count

    if date_start and date_end:
        output, stats.date_ranges = replace_event_day_between(output, date_start, date_end)

    return output, stats


def read_input(path: str | None) -> str:
    if not path or path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def write_output(path: str | None, text: str) -> None:
    if path:
        Path(path).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Replace SQL experiment ids and event_day between ranges deterministically.",
    )
    parser.add_argument("sql_file", nargs="?", help="SQL input file. Omit or use '-' to read stdin.")
    parser.add_argument("--out-file", help="Write transformed SQL to this file instead of stdout.")
    parser.add_argument(
        "--map",
        dest="mappings",
        action="append",
        type=parse_replacement,
        default=[],
        metavar="OLD=NEW",
        help="Experiment token mapping. Base ids preserve -0/-dz suffixes; repeat for multiple mappings.",
    )
    parser.add_argument("--date-start", help="New event_day start date, YYYYMMDD or MMDD with --year.")
    parser.add_argument("--date-end", help="New event_day end date, YYYYMMDD or MMDD with --year.")
    parser.add_argument("--year", help="Year used to expand MMDD dates, for example 2026.")
    parser.add_argument(
        "--allow-zero",
        action="store_true",
        help="Do not fail when a requested mapping or date range is not found.",
    )
    parser.add_argument("--quiet", action="store_true", help="Do not print replacement counts to stderr.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if bool(args.date_start) != bool(args.date_end):
        parser.error("--date-start and --date-end must be provided together")

    try:
        date_start = normalize_date(args.date_start, args.year) if args.date_start else None
        date_end = normalize_date(args.date_end, args.year) if args.date_end else None
    except ValueError as exc:
        parser.error(str(exc))

    sql = read_input(args.sql_file)
    output, stats = transform_sql(sql, args.mappings, date_start, date_end)

    missing: list[str] = []
    for mapping, count in (stats.experiment_counts or {}).items():
        if count == 0:
            missing.append(f"mapping {mapping!r} matched 0 tokens")
    if date_start and date_end and stats.date_ranges == 0:
        missing.append("event_day between matched 0 ranges")

    if missing and not args.allow_zero:
        for item in missing:
            print(f"ERROR: {item}", file=sys.stderr)
        return 2

    write_output(args.out_file, output)

    if not args.quiet:
        for mapping, count in (stats.experiment_counts or {}).items():
            print(f"replaced {mapping}: {count}", file=sys.stderr)
        if date_start and date_end:
            print(f"replaced event_day between: {stats.date_ranges}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
