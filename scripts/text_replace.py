#!/usr/bin/env python3
"""Apply explicit text replacement plans with counts and failure checks.

This is the generic deterministic layer. Domain scripts should decide *what*
to replace, then call this module to do the mechanical replacement.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Pattern


TOKEN_CHARS = r"A-Za-z0-9_-"
TOKEN_LEFT_BOUNDARY = rf"(?<![{TOKEN_CHARS}])"
TOKEN_RIGHT_BOUNDARY = rf"(?![{TOKEN_CHARS}])"


@dataclass(frozen=True)
class ReplacementRule:
    name: str
    kind: str
    old: str | None = None
    new: str | None = None
    pattern: str | None = None
    replacement: str | None = None
    suffixes: tuple[str, ...] = ()
    expect_min: int = 1


@dataclass
class ReplacementResult:
    text: str
    counts: dict[str, int] = field(default_factory=dict)


def parse_mapping(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError(f"mapping must use OLD=NEW format: {value!r}")
    old, new = (part.strip() for part in value.split("=", 1))
    if not old or not new:
        raise argparse.ArgumentTypeError(f"mapping must not contain empty sides: {value!r}")
    return old, new


def read_input(path: str | None) -> str:
    if not path or path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def write_output(path: str | None, text: str) -> None:
    if path:
        Path(path).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def token_pattern(old: str, suffixes: tuple[str, ...] = ()) -> Pattern[str]:
    suffix_part = ""
    if suffixes:
        suffix_alt = "|".join(re.escape(suffix) for suffix in suffixes)
        suffix_part = rf"(?P<suffix>{suffix_alt})?"
    return re.compile(rf"{TOKEN_LEFT_BOUNDARY}{re.escape(old)}{suffix_part}{TOKEN_RIGHT_BOUNDARY}")


def apply_regex_callback(
    text: str,
    name: str,
    pattern: Pattern[str],
    callback: Callable[[re.Match[str]], str],
) -> tuple[str, int]:
    count = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        replacement = callback(match)
        if replacement != match.group(0):
            count += 1
        return replacement

    return pattern.sub(repl, text), count


def apply_rule(text: str, rule: ReplacementRule) -> tuple[str, int]:
    if rule.kind == "literal":
        if rule.old is None or rule.new is None:
            raise ValueError(f"literal rule {rule.name!r} requires old and new")
        count = text.count(rule.old)
        return text.replace(rule.old, rule.new), count

    if rule.kind == "token":
        if rule.old is None or rule.new is None:
            raise ValueError(f"token rule {rule.name!r} requires old and new")
        pattern = token_pattern(rule.old, rule.suffixes)

        def repl(match: re.Match[str]) -> str:
            return f"{rule.new}{match.groupdict().get('suffix') or ''}"

        return pattern.subn(repl, text)

    if rule.kind == "regex":
        if rule.pattern is None or rule.replacement is None:
            raise ValueError(f"regex rule {rule.name!r} requires pattern and replacement")
        return re.subn(rule.pattern, rule.replacement, text)

    raise ValueError(f"unsupported replacement rule kind: {rule.kind!r}")


def apply_token_rules(text: str, rules: list[ReplacementRule]) -> ReplacementResult:
    if not rules:
        return ReplacementResult(text=text)

    seen_old: set[str] = set()
    alternatives: list[str] = []
    for index, rule in enumerate(rules):
        if rule.kind != "token":
            raise ValueError("apply_token_rules only accepts token rules")
        if rule.old is None or rule.new is None:
            raise ValueError(f"token rule {rule.name!r} requires old and new")
        if rule.old in seen_old:
            raise ValueError(f"duplicate token old value: {rule.old!r}")
        seen_old.add(rule.old)

        suffix_part = ""
        if rule.suffixes:
            suffix_alt = "|".join(re.escape(suffix) for suffix in rule.suffixes)
            suffix_part = rf"(?P<s{index}>{suffix_alt})?"
        alternatives.append(rf"(?P<r{index}>{re.escape(rule.old)}){suffix_part}")

    pattern = re.compile(rf"{TOKEN_LEFT_BOUNDARY}(?:{'|'.join(alternatives)}){TOKEN_RIGHT_BOUNDARY}")
    counts = {rule.name: 0 for rule in rules}

    def repl(match: re.Match[str]) -> str:
        for index, rule in enumerate(rules):
            if match.group(f"r{index}") is None:
                continue
            counts[rule.name] += 1
            suffix = match.groupdict().get(f"s{index}") or ""
            return f"{rule.new}{suffix}"
        return match.group(0)

    return ReplacementResult(text=pattern.sub(repl, text), counts=counts)


def apply_rules(text: str, rules: list[ReplacementRule]) -> ReplacementResult:
    output = text
    counts: dict[str, int] = {}
    index = 0
    while index < len(rules):
        rule = rules[index]
        if rule.kind == "token":
            next_index = index
            while next_index < len(rules) and rules[next_index].kind == "token":
                next_index += 1
            result = apply_token_rules(output, rules[index:next_index])
            output = result.text
            counts.update(result.counts)
            index = next_index
            continue

        output, count = apply_rule(output, rule)
        counts[rule.name] = count
        index += 1
    return ReplacementResult(text=output, counts=counts)


def rules_from_plan(plan: dict[str, object]) -> list[ReplacementRule]:
    raw_rules = plan.get("rules")
    if not isinstance(raw_rules, list):
        raise ValueError("plan must contain a rules list")

    rules: list[ReplacementRule] = []
    for index, raw_rule in enumerate(raw_rules):
        if not isinstance(raw_rule, dict):
            raise ValueError(f"rule {index} must be an object")

        kind = str(raw_rule.get("kind") or "")
        name = str(raw_rule.get("name") or f"{kind}:{index}")
        suffixes_raw = raw_rule.get("suffixes") or []
        if not isinstance(suffixes_raw, list):
            raise ValueError(f"rule {name!r} suffixes must be a list")
        expect_min = int(raw_rule.get("expect_min", 1))

        rules.append(
            ReplacementRule(
                name=name,
                kind=kind,
                old=str(raw_rule["old"]) if "old" in raw_rule else None,
                new=str(raw_rule["new"]) if "new" in raw_rule else None,
                pattern=str(raw_rule["pattern"]) if "pattern" in raw_rule else None,
                replacement=str(raw_rule["replacement"]) if "replacement" in raw_rule else None,
                suffixes=tuple(str(item) for item in suffixes_raw),
                expect_min=expect_min,
            )
        )
    return rules


def load_plan(path: str) -> list[ReplacementRule]:
    return rules_from_plan(json.loads(Path(path).read_text(encoding="utf-8")))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply explicit text replacement rules.")
    parser.add_argument("input_file", nargs="?", help="Input text file. Omit or use '-' to read stdin.")
    parser.add_argument("--out-file", help="Write transformed text to this file instead of stdout.")
    parser.add_argument("--plan-file", help="JSON replacement plan file.")
    parser.add_argument("--literal", action="append", default=[], metavar="OLD=NEW", help="Literal replacement.")
    parser.add_argument("--token", action="append", default=[], metavar="OLD=NEW", help="Token-boundary replacement.")
    parser.add_argument("--regex", action="append", default=[], metavar="PATTERN=REPL", help="Regex replacement.")
    parser.add_argument(
        "--suffix",
        action="append",
        default=[],
        help="Suffixes preserved for direct --token rules. For dash-prefixed values, use --suffix=-0. Repeat as needed.",
    )
    parser.add_argument("--allow-zero", action="store_true", help="Do not fail when a rule matches less than expect_min.")
    parser.add_argument("--dry-run", action="store_true", help="Print replacement counts as JSON instead of text output.")
    parser.add_argument("--quiet", action="store_true", help="Do not print replacement counts to stderr.")
    return parser


def direct_rules(args: argparse.Namespace) -> list[ReplacementRule]:
    rules: list[ReplacementRule] = []
    for value in args.literal:
        old, new = parse_mapping(value)
        rules.append(ReplacementRule(name=f"literal:{old}={new}", kind="literal", old=old, new=new))
    for value in args.token:
        old, new = parse_mapping(value)
        rules.append(
            ReplacementRule(
                name=f"token:{old}={new}",
                kind="token",
                old=old,
                new=new,
                suffixes=tuple(args.suffix),
            )
        )
    for value in args.regex:
        pattern, replacement = parse_mapping(value)
        rules.append(
            ReplacementRule(
                name=f"regex:{pattern}",
                kind="regex",
                pattern=pattern,
                replacement=replacement,
            )
        )
    return rules


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    rules = load_plan(args.plan_file) if args.plan_file else direct_rules(args)
    if not rules:
        parser.error("provide --plan-file or at least one replacement rule")

    text = read_input(args.input_file)
    result = apply_rules(text, rules)

    missing = [rule for rule in rules if result.counts.get(rule.name, 0) < rule.expect_min]
    if missing and not args.allow_zero:
        for rule in missing:
            actual = result.counts.get(rule.name, 0)
            print(f"ERROR: rule {rule.name!r} matched {actual}, expected at least {rule.expect_min}", file=sys.stderr)
        return 2

    if args.dry_run:
        json.dump(result.counts, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        write_output(args.out_file, result.text)

    if not args.quiet:
        for name, count in result.counts.items():
            print(f"replaced {name}: {count}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
