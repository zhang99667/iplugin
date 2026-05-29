#!/usr/bin/env python3
"""Scan SQL, then deterministically replace confirmed experiment ids and dates.

The script intentionally handles only mechanical replacement. The calling
assistant should inspect SQL semantics and resolve ambiguous fields or mappings
before invoking replacement mode.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass

try:
    from scripts.text_replace import ReplacementRule, apply_regex_callback, apply_rules, read_input, write_output
except ModuleNotFoundError:
    from text_replace import ReplacementRule, apply_regex_callback, apply_rules, read_input, write_output


TOKEN_RE = re.compile(r"^[A-Za-z0-9_]+(?:-(?:0|dz))?$")
DATE_RE = re.compile(r"^\d{8}$")
SHORT_DATE_RE = re.compile(r"^\d{4}$")
YEAR_RE = re.compile(r"^\d{4}$")
IDENT_PART_RE = r"(?:`[^`]+`|[A-Za-z_][A-Za-z0-9_]*)"
FIELD_EXPR_RE = rf"{IDENT_PART_RE}(?:\s*\.\s*{IDENT_PART_RE})*"
DATE_BETWEEN_RE = re.compile(
    rf"(?i)(?P<prefix>(?P<field>{FIELD_EXPR_RE})\s+between\s*)"
    r"(?P<q1>['\"]?)(?P<start>\d{8})(?P=q1)"
    r"(?P<separator>\s+and\s*)"
    r"(?P<q2>['\"]?)(?P<end>\d{8})(?P=q2)"
)
EXPERIMENT_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_-])(?P<token>[A-Za-z0-9_]+-(?:0|dz))(?![A-Za-z0-9_-])")
STANDALONE_NUMERIC_RE = re.compile(r"(?<![A-Za-z0-9_-])(?P<token>\d{5,})(?![A-Za-z0-9_-])")


@dataclass(frozen=True)
class Replacement:
    old: str
    new: str


@dataclass
class ReplacementStats:
    date_ranges: int = 0
    date_field_counts: dict[str, int] | None = None
    experiment_counts: dict[str, int] | None = None

    def __post_init__(self) -> None:
        if self.date_field_counts is None:
            self.date_field_counts = {}
        if self.experiment_counts is None:
            self.experiment_counts = {}


def normalize_field(value: str) -> str:
    return re.sub(r"\s+", "", value).replace("`", "").lower()


def field_matches(candidate: str, requested: str) -> bool:
    candidate_norm = normalize_field(candidate)
    requested_norm = normalize_field(requested)
    if candidate_norm == requested_norm:
        return True
    if "." in requested_norm:
        return False
    return candidate_norm.rsplit(".", 1)[-1] == requested_norm


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
        if not YEAR_RE.fullmatch(year):
            raise ValueError(f"--year must be four digits when expanding MMDD: {year!r}")
        return f"{year}{value}"
    raise ValueError(f"date must be YYYYMMDD or MMDD: {value!r}")


def line_number(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def scan_sql(sql: str) -> dict[str, object]:
    experiments: dict[str, dict[str, int]] = {}
    for match in EXPERIMENT_TOKEN_RE.finditer(sql):
        token = match.group("token")
        base, suffix = token.rsplit("-", 1)
        bucket = experiments.setdefault(base, {"total": 0, "experiment": 0, "control": 0})
        bucket["total"] += 1
        if suffix == "0":
            bucket["experiment"] += 1
        elif suffix == "dz":
            bucket["control"] += 1

    standalone_numeric_tokens: dict[str, int] = {}
    for match in STANDALONE_NUMERIC_RE.finditer(sql):
        token = match.group("token")
        if DATE_RE.fullmatch(token):
            continue
        standalone_numeric_tokens[token] = standalone_numeric_tokens.get(token, 0) + 1

    date_between: list[dict[str, object]] = []
    for match in DATE_BETWEEN_RE.finditer(sql):
        date_between.append(
            {
                "field": re.sub(r"\s+", "", match.group("field")),
                "start": match.group("start"),
                "end": match.group("end"),
                "line": line_number(sql, match.start()),
            }
        )

    return {
        "experiment_bases": experiments,
        "standalone_numeric_tokens": standalone_numeric_tokens,
        "date_between": date_between,
    }


def matching_date_field(candidate: str, fields: list[str]) -> str | None:
    candidate_norm = normalize_field(candidate)
    for field in fields:
        if candidate_norm == normalize_field(field):
            return field
    for field in fields:
        if "." not in normalize_field(field) and field_matches(candidate, field):
            return field
    return None


def replace_date_between(sql: str, fields: list[str], start: str, end: str) -> tuple[str, dict[str, int]]:
    field_counts = {field: 0 for field in fields}

    def repl(match: re.Match[str]) -> str:
        matched_field = matching_date_field(match.group("field"), fields)
        if matched_field is None:
            return match.group(0)
        field_counts[matched_field] += 1
        return (
            f"{match.group('prefix')}"
            f"{match.group('q1')}{start}{match.group('q1')}"
            f"{match.group('separator')}"
            f"{match.group('q2')}{end}{match.group('q2')}"
        )

    output, _ = apply_regex_callback(sql, "date-between", DATE_BETWEEN_RE, repl)
    return output, field_counts


def experiment_rule(replacement: Replacement) -> ReplacementRule:
    suffixes = ()
    if "-" not in replacement.old and "-" not in replacement.new:
        suffixes = ("-0", "-dz")
    return ReplacementRule(
        name=f"{replacement.old}={replacement.new}",
        kind="token",
        old=replacement.old,
        new=replacement.new,
        suffixes=suffixes,
    )


def replace_experiment(sql: str, replacement: Replacement) -> tuple[str, int]:
    rule = experiment_rule(replacement)
    result = apply_rules(sql, [rule])
    return result.text, result.counts[rule.name]


def replace_experiments(sql: str, replacements: list[Replacement]) -> tuple[str, dict[str, int]]:
    rules = [experiment_rule(replacement) for replacement in replacements]
    result = apply_rules(sql, rules)
    return result.text, result.counts


def transform_sql(
    sql: str,
    replacements: list[Replacement],
    date_start: str | None,
    date_end: str | None,
    date_fields: list[str] | None = None,
) -> tuple[str, ReplacementStats]:
    stats = ReplacementStats()
    output = sql

    if replacements:
        output, counts = replace_experiments(output, replacements)
        assert stats.experiment_counts is not None
        stats.experiment_counts.update(counts)

    if date_start and date_end:
        output, field_counts = replace_date_between(output, date_fields or ["event_day"], date_start, date_end)
        stats.date_field_counts = field_counts
        stats.date_ranges = sum(field_counts.values())

    return output, stats


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scan SQL and replace confirmed experiment ids/date ranges deterministically.",
    )
    parser.add_argument("sql_file", nargs="?", help="SQL input file. Omit or use '-' to read stdin.")
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Only scan SQL and print candidate experiment ids/date fields as JSON.",
    )
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
    parser.add_argument(
        "--date-field",
        action="append",
        default=[],
        help="Date field to update in BETWEEN predicates. Repeat for multiple fields. Defaults to event_day.",
    )
    parser.add_argument("--date-start", help="New date range start, YYYYMMDD or MMDD with --year.")
    parser.add_argument("--date-end", help="New date range end, YYYYMMDD or MMDD with --year.")
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

    sql = read_input(args.sql_file)

    if args.scan:
        json.dump(scan_sql(sql), sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0

    if bool(args.date_start) != bool(args.date_end):
        parser.error("--date-start and --date-end must be provided together")

    try:
        date_start = normalize_date(args.date_start, args.year) if args.date_start else None
        date_end = normalize_date(args.date_end, args.year) if args.date_end else None
    except ValueError as exc:
        parser.error(str(exc))

    output, stats = transform_sql(sql, args.mappings, date_start, date_end, args.date_field)

    missing: list[str] = []
    for mapping, count in (stats.experiment_counts or {}).items():
        if count == 0:
            missing.append(f"mapping {mapping!r} matched 0 tokens")
    if date_start and date_end:
        for field, count in (stats.date_field_counts or {}).items():
            if count == 0:
                missing.append(f"date between matched 0 ranges for field: {field}")

    if missing and not args.allow_zero:
        for item in missing:
            print(f"ERROR: {item}", file=sys.stderr)
        return 2

    write_output(args.out_file, output)

    if not args.quiet:
        for mapping, count in (stats.experiment_counts or {}).items():
            print(f"replaced {mapping}: {count}", file=sys.stderr)
        if date_start and date_end:
            for field, count in (stats.date_field_counts or {}).items():
                print(f"replaced date between for {field}: {count}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
