#!/usr/bin/env python3
"""校验 iPlugin 的 manifest、skills、commands 和版本记录。

脚本保持只读，并且只依赖 Python 标准库，方便在全新 checkout 后直接运行。
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

# 仓库内需要共同参与一致性检查的核心文件和目录。
CLAUDE_MANIFEST = ROOT / ".claude-plugin" / "plugin.json"
CODEX_MANIFEST = ROOT / ".codex-plugin" / "plugin.json"
CLAUDE_MD = ROOT / "CLAUDE.md"
AGENTS_MD = ROOT / "AGENTS.md"
README = ROOT / "README.md"
CHANGELOG = ROOT / "CHANGELOG.md"
SKILLS_DIR = ROOT / "skills"
COMMANDS_DIR = ROOT / "commands"
VERSIONS_DIR = ROOT / "versions"

# 两个平台 manifest 中必须保持一致的公共字段。
PRIMARY_COMMON_FIELDS = ("name", "version", "description", "keywords")
PLATFORM_SPECIFIC_FIELDS = {"commands", "hooks", "interface", "skills"}

# 只有在 slash 用法附近出现这些语义时，才认为它是在声明 slash command。
SLASH_COMMAND_CONTEXT = (
    "command",
    "slash",
    "invoked",
    "命令",
    "调用",
    "触发",
    "入口",
    "使用",
    "用户通过",
)

# 常见路径片段，避免把 /usr、/tmp 这类文件路径误判成 slash command。
PATH_LIKE_SLASH_NAMES = {
    "abs",
    "absolute",
    "applications",
    "bin",
    "dev",
    "etc",
    "home",
    "opt",
    "path",
    "private",
    "repo",
    "tmp",
    "usr",
    "var",
}


@dataclass
class CheckResult:
    """单项检查结果：details 为空表示通过，否则表示失败原因。"""

    name: str
    details: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.details


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> tuple[Any | None, str | None]:
    try:
        return json.loads(read_text(path)), None
    except FileNotFoundError:
        return None, f"{rel(path)} does not exist"
    except json.JSONDecodeError as exc:
        return None, f"{rel(path)} is not valid JSON: {exc.msg} at line {exc.lineno}, column {exc.colno}"


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_inline_list(value: str) -> list[str]:
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        return [strip_quotes(value)] if value else []
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [strip_quotes(part) for part in inner.split(",") if strip_quotes(part)]


def parse_frontmatter(path: Path) -> tuple[dict[str, Any], str | None]:
    """解析 SKILL.md / command markdown 中使用的简单 YAML frontmatter。

    本仓库 frontmatter 只需要覆盖 key: value 和缩进列表两种形式，
    因此这里不用额外引入 PyYAML。
    """

    try:
        text = read_text(path)
    except FileNotFoundError:
        return {}, f"{rel(path)} does not exist"

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, f"{rel(path)} is missing YAML frontmatter"

    end_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = index
            break
    if end_index is None:
        return {}, f"{rel(path)} has unterminated YAML frontmatter"

    data: dict[str, Any] = {}
    current_key: str | None = None
    for raw_line in lines[1:end_index]:
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        list_match = re.match(r"\s*-\s*(.+?)\s*$", raw_line)
        if list_match and current_key:
            if not isinstance(data.get(current_key), list):
                data[current_key] = []
            data[current_key].append(strip_quotes(list_match.group(1)))
            continue

        key_match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$", raw_line)
        if not key_match:
            current_key = None
            continue

        key, value = key_match.groups()
        value = value.strip()
        current_key = key
        if value.startswith("[") and value.endswith("]"):
            data[key] = parse_inline_list(value)
        elif value:
            data[key] = strip_quotes(value)
        else:
            data[key] = []

    return data, None


def skill_dirs() -> list[Path]:
    if not SKILLS_DIR.is_dir():
        return []
    return sorted(path for path in SKILLS_DIR.iterdir() if path.is_dir())


def command_files() -> set[str]:
    if not COMMANDS_DIR.is_dir():
        return set()
    return {path.stem for path in COMMANDS_DIR.glob("*.md") if path.is_file()}


def check_json_manifests() -> tuple[CheckResult, dict[str, Any] | None, dict[str, Any] | None]:
    """检查 Claude / Codex 两份 plugin.json 是否是合法 JSON 对象。"""

    result = CheckResult("Manifest JSON is valid")
    claude, claude_error = load_json(CLAUDE_MANIFEST)
    codex, codex_error = load_json(CODEX_MANIFEST)
    for error in (claude_error, codex_error):
        if error:
            result.details.append(error)
    if claude is not None and not isinstance(claude, dict):
        result.details.append(f"{rel(CLAUDE_MANIFEST)} must contain a JSON object")
    if codex is not None and not isinstance(codex, dict):
        result.details.append(f"{rel(CODEX_MANIFEST)} must contain a JSON object")
    return result, claude if isinstance(claude, dict) else None, codex if isinstance(codex, dict) else None


def check_manifest_common_fields(claude: dict[str, Any] | None, codex: dict[str, Any] | None) -> CheckResult:
    """检查两个平台 manifest 的公共字段是否保持同步。"""

    result = CheckResult("Manifest common fields match")
    if claude is None or codex is None:
        result.details.append("Skipped because at least one manifest could not be loaded")
        return result

    fields = list(PRIMARY_COMMON_FIELDS)
    extra_common = sorted((set(claude) & set(codex)) - set(fields) - PLATFORM_SPECIFIC_FIELDS)
    fields.extend(extra_common)

    for field_name in fields:
        if field_name not in claude:
            result.details.append(f"{rel(CLAUDE_MANIFEST)} is missing common field {field_name!r}")
            continue
        if field_name not in codex:
            result.details.append(f"{rel(CODEX_MANIFEST)} is missing common field {field_name!r}")
            continue
        if claude[field_name] != codex[field_name]:
            result.details.append(
                f"Field {field_name!r} differs between manifests: "
                f"claude={claude[field_name]!r}, codex={codex[field_name]!r}"
            )

    return result


def check_skills_frontmatter(skills: list[Path]) -> tuple[CheckResult, dict[str, dict[str, Any]]]:
    """检查 skills/<name>/SKILL.md 的 frontmatter 和目录名是否一致。"""

    result = CheckResult("Skill frontmatter is valid")
    metadata: dict[str, dict[str, Any]] = {}

    if not SKILLS_DIR.is_dir():
        result.details.append("skills/ directory does not exist")
        return result, metadata

    for skill_dir in skills:
        skill_name = skill_dir.name
        skill_file = skill_dir / "SKILL.md"
        data, error = parse_frontmatter(skill_file)
        if error:
            result.details.append(error)
            continue

        metadata[skill_name] = data
        if data.get("name") != skill_name:
            result.details.append(
                f"{rel(skill_file)} frontmatter name must be {skill_name!r}, got {data.get('name')!r}"
            )
        for required in ("version", "description", "tags"):
            value = data.get(required)
            if value in (None, "", []):
                result.details.append(f"{rel(skill_file)} is missing non-empty frontmatter field {required!r}")

    return result, metadata


def extract_readme_skill_names() -> tuple[set[str], list[str]]:
    """从 README 的 Skills 表格中提取声明的 skill 名称。"""

    try:
        text = read_text(README)
    except FileNotFoundError:
        return set(), [f"{rel(README)} does not exist"]

    section_match = re.search(r"^## Skills\s*$([\s\S]*?)(?=^## |\Z)", text, re.MULTILINE)
    if not section_match:
        return set(), [f"{rel(README)} is missing a '## Skills' section"]

    section = section_match.group(1)
    names = set(re.findall(r"^\|\s*`([^`]+)`\s*\|", section, re.MULTILINE))
    if not names:
        return names, [f"{rel(README)} Skills section has no skill table rows"]
    return names, []


def check_readme_skills(skills: list[Path]) -> CheckResult:
    """检查 README Skills 表和实际 skills/ 目录是否互相覆盖。"""

    result = CheckResult("README Skills table matches skills/")
    readme_names, errors = extract_readme_skill_names()
    result.details.extend(errors)
    if errors:
        return result

    actual_names = {path.name for path in skills}
    missing = sorted(actual_names - readme_names)
    extra = sorted(readme_names - actual_names)
    if missing:
        result.details.append(f"{rel(README)} is missing skill rows: {', '.join(missing)}")
    if extra:
        result.details.append(f"{rel(README)} contains skill rows without matching directories: {', '.join(extra)}")
    return result


def required_keyword_tokens(skills: list[Path]) -> set[str]:
    """生成 manifest keywords 至少应覆盖的 skill 名称和拆分词。"""

    required: set[str] = set()
    for skill_dir in skills:
        name = skill_dir.name
        required.add(name)
        required.update(token for token in name.split("-") if token)
    return required


def check_manifest_keywords(claude: dict[str, Any] | None, codex: dict[str, Any] | None, skills: list[Path]) -> CheckResult:
    """检查 manifest keywords 是否覆盖所有 skill 名称及 kebab 拆分词。"""

    result = CheckResult("Manifest keywords cover skill names and kebab tokens")
    if claude is None or codex is None:
        result.details.append("Skipped because at least one manifest could not be loaded")
        return result

    required = required_keyword_tokens(skills)
    for manifest_path, manifest in ((CLAUDE_MANIFEST, claude), (CODEX_MANIFEST, codex)):
        keywords = manifest.get("keywords")
        if not isinstance(keywords, list) or not all(isinstance(item, str) for item in keywords):
            result.details.append(f"{rel(manifest_path)} field 'keywords' must be a list of strings")
            continue
        missing = sorted(required - set(keywords))
        if missing:
            result.details.append(f"{rel(manifest_path)} keywords missing: {', '.join(missing)}")
    return result


def check_changelog_versions() -> CheckResult:
    """检查 CHANGELOG 中每个版本都有对应的 versions 记录。"""

    result = CheckResult("CHANGELOG versions have version docs")
    try:
        text = read_text(CHANGELOG)
    except FileNotFoundError:
        result.details.append(f"{rel(CHANGELOG)} does not exist")
        return result

    versions = re.findall(r"^## \[([0-9]+\.[0-9]+\.[0-9]+)\]", text, re.MULTILINE)
    for version in versions:
        file_path = VERSIONS_DIR / f"v{version}.md"
        dir_path = VERSIONS_DIR / f"v{version}"
        if not file_path.is_file() and not dir_path.is_dir():
            result.details.append(
                f"{rel(CHANGELOG)} entry [{version}] is missing {rel(file_path)} or {rel(dir_path)}/"
            )
    return result


def strip_fenced_code(text: str) -> str:
    return re.sub(r"```[\s\S]*?```", "", text)


def strip_urls(text: str) -> str:
    return re.sub(r"https?://\S+", "", text)


def is_between_inline_backticks(line: str, index: int) -> bool:
    return line[:index].count("`") % 2 == 1


def is_quoted(line: str, index: int, end_index: int) -> bool:
    before = line[index - 1] if index > 0 else ""
    after = line[end_index] if end_index < len(line) else ""
    return before in {"'", '"', "“", "‘", "`"} or after in {"'", '"', "”", "’", "`"}


def slash_command_candidates(path: Path) -> set[str]:
    """从 README / SKILL.md 中提取看起来像 slash command 声明的名称。

    这里会先去掉代码块和 URL，再结合上下文关键词、反引号/引号包裹、
    README 表格行等信号，尽量避免把普通路径误报为 command。
    """

    text = strip_urls(strip_fenced_code(read_text(path)))
    candidates: set[str] = set()
    pattern = re.compile(r"(^|[\s([{\"'“‘、，。；;:：])/([a-z][a-z0-9-]*)(?![A-Za-z0-9_-])")

    for line in text.splitlines():
        for match in pattern.finditer(line):
            name = match.group(2)
            start = match.start(2) - 1
            end = match.end(2)
            following = line[end] if end < len(line) else ""
            if following in {"/", "."}:
                continue
            if name in PATH_LIKE_SLASH_NAMES:
                continue

            window = line[max(0, start - 40) : min(len(line), end + 40)].lower()
            has_command_context = any(word.lower() in window for word in SLASH_COMMAND_CONTEXT)
            has_delimited_context = is_between_inline_backticks(line, start) or is_quoted(line, start, end)
            in_readme_skills_table = path == README and line.lstrip().startswith("|")
            if has_command_context or has_delimited_context or in_readme_skills_table:
                candidates.add(name)

    return candidates


def check_commands(skill_names: set[str]) -> CheckResult:
    """检查 command 文件引用的 skill 存在，且文档声明的 slash command 有入口文件。"""

    result = CheckResult("Command references are valid")
    commands = command_files()

    if COMMANDS_DIR.is_dir():
        for command_file in sorted(COMMANDS_DIR.glob("*.md")):
            text = read_text(command_file)
            for skill_name in re.findall(r"skills/([A-Za-z0-9][A-Za-z0-9_-]*)/SKILL\.md", text):
                if skill_name not in skill_names:
                    result.details.append(
                        f"{rel(command_file)} references missing skill skills/{skill_name}/SKILL.md"
                    )

    scan_files = [README]
    scan_files.extend(skill_dir / "SKILL.md" for skill_dir in skill_dirs())
    for scan_file in scan_files:
        if not scan_file.is_file():
            continue
        for command_name in sorted(slash_command_candidates(scan_file)):
            if command_name not in commands:
                result.details.append(
                    f"{rel(scan_file)} mentions /{command_name}, but {rel(COMMANDS_DIR / (command_name + '.md'))} does not exist"
                )

    return result


def check_claude_agents_sync() -> CheckResult:
    """检查 CLAUDE.md 与 AGENTS.md 内容是否完全一致（SHA-256 哈希对比）。"""

    result = CheckResult("CLAUDE.md and AGENTS.md are in sync")
    for path in (CLAUDE_MD, AGENTS_MD):
        if not path.is_file():
            result.details.append(f"{rel(path)} does not exist")
    if result.details:
        return result

    hash_claude = hashlib.sha256(CLAUDE_MD.read_bytes()).hexdigest()
    hash_agents = hashlib.sha256(AGENTS_MD.read_bytes()).hexdigest()
    if hash_claude != hash_agents:
        result.details.append(
            f"CLAUDE.md and AGENTS.md differ — update both files to keep them in sync"
        )
    return result


def check_no_hardcoded_homedir(skills: list[Path]) -> CheckResult:
    """检查 skills/ 下的 SKILL.md 主文件是否存在硬编码的绝对用户主目录路径。

    只检查 SKILL.md 主文件，跳过 references/ 子目录（示例文档中的路径是合法内容）。
    """

    result = CheckResult("No hardcoded absolute home paths in skills/")
    pattern = re.compile(r"/Users/[^/\s'\"]+")
    for skill_dir in skills:
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        text = read_text(skill_md)
        matches = pattern.findall(text)
        if matches:
            unique = sorted(set(matches))
            result.details.append(
                f"{rel(skill_md)} contains hardcoded path(s): {', '.join(unique)}"
            )
    return result


def print_results(results: list[CheckResult]) -> None:
    """按固定格式输出所有检查项，便于提交前快速扫一眼。"""

    width = max(len(result.name) for result in results)
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status}  {result.name.ljust(width)}")
        for detail in result.details:
            print(f"      - {detail}")

    failed = sum(1 for result in results if not result.passed)
    total = len(results)
    print()
    if failed:
        print(f"Summary: {failed}/{total} checks failed.")
    else:
        print(f"Summary: all {total} checks passed.")


def main() -> int:
    """执行全部校验；任一检查失败时返回非零退出码。"""

    json_result, claude_manifest, codex_manifest = check_json_manifests()
    skills = skill_dirs()
    skill_names = {path.name for path in skills}
    frontmatter_result, _ = check_skills_frontmatter(skills)

    results = [
        json_result,
        check_manifest_common_fields(claude_manifest, codex_manifest),
        frontmatter_result,
        check_readme_skills(skills),
        check_manifest_keywords(claude_manifest, codex_manifest, skills),
        check_changelog_versions(),
        check_commands(skill_names),
        check_claude_agents_sync(),
        check_no_hardcoded_homedir(skills),
    ]

    print_results(results)
    return 1 if any(not result.passed for result in results) else 0


if __name__ == "__main__":
    sys.exit(main())
