#!/usr/bin/env python3
"""校验 iPlugin 的 manifest、活跃/退役 skills、commands 和版本记录。

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
DEPRECATED_SKILLS_DIR = ROOT / "deprecated-skills"
DEPRECATED_SKILLS_README = DEPRECATED_SKILLS_DIR / "README.md"
COMMANDS_DIR = ROOT / "commands"
VERSIONS_DIR = ROOT / "versions"
HOOKS_DIR = ROOT / "hooks"
EVALS_RELATIVE_PATH = Path("evals/evals.json")
HTML_REPORT_ANNOTATION_ASSETS = {
    SKILLS_DIR / "html-report" / "assets" / "annotation-mode" / "annotation.css": (
        "QA_ANNOTATION_CSS_START",
        "QA_ANNOTATION_CSS_END",
        ".qa-shortcut-hint",
        ".qa-launcher-count[hidden]",
    ),
    SKILLS_DIR / "html-report" / "assets" / "annotation-mode" / "annotation.html": (
        "QA_ANNOTATION_HTML_START",
        "QA_ANNOTATION_HTML_END",
        'id="qaSaveReviewHtml"',
        '<span class="qa-launcher-label" id="qaLauncherLabel">批注</span>',
        "完成批注",
        'data-qa-action="note-selection" title="添加注释"',
        '<kbd class="qa-shortcut-hint" aria-hidden="true">Ctrl/⌘ + Enter</kbd>',
    ),
    SKILLS_DIR / "html-report" / "assets" / "annotation-mode" / "annotation.js": (
        "QA_ANNOTATION_SCRIPT_START",
        "QA_ANNOTATION_SCRIPT_END",
        "__QA_REPORT_META__",
        "buildReviewedHtml",
        "serializeReviewPack",
        "readEmbeddedReviewPack",
        "legacyStorageKey",
        "launcherLabel.textContent = '批注'",
        "launcherCount.hidden = count === 0",
        "setSidebarOpen(!sidebar.classList.contains('open'))",
        "reviewFallbackFileName",
    ),
}
HTML_REPORT_REVIEW_WORKSPACE_ASSETS = {
    SKILLS_DIR / "html-report" / "assets" / "review-workspace" / "workspace.js": (
        "HTML_REPORT_REVIEW_WORKSPACE_RUNTIME_START",
        "HTML_REPORT_REVIEW_WORKSPACE_RUNTIME_END",
        "HtmlReportReviewWorkspace",
        "data-review-workspace-root",
        "rw-diff-only",
        "document.execCommand",
    ),
    SKILLS_DIR / "html-report" / "assets" / "review-workspace" / "workspace.css": (
        ".review-workspace .rw-toolbar",
        ".review-workspace .rw-panes",
        ".review-workspace .rw-code-scroll",
        ".review-workspace.rw-diff-only",
        "@media print",
    ),
    SKILLS_DIR / "html-report" / "scripts" / "build_review_workspace.py": (
        "script_safe_json",
        "render_fragment",
        "render_standalone",
        "workspace.js",
        "assemble_html",
    ),
}
HTML_REPORT_COMPONENT_ROOT = SKILLS_DIR / "html-report" / "assets" / "components"
HTML_REPORT_COMPONENT_REGISTRY = HTML_REPORT_COMPONENT_ROOT / "registry.json"

# 两个平台 manifest 中必须保持一致的公共字段。
PRIMARY_COMMON_FIELDS = ("name", "version", "description", "keywords")
PLATFORM_SPECIFIC_FIELDS = {"commands", "hooks", "interface", "skills"}
PLUGIN_VERSION_RE = re.compile(r"^([0-9]+)\.([0-9]+)\.([0-9]+)$")

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


def deprecated_skill_dirs() -> list[Path]:
    """只读取顶层退役目录，避免把其 references/scripts 误当成独立 skill。"""

    if not DEPRECATED_SKILLS_DIR.is_dir():
        return []
    return sorted(path for path in DEPRECATED_SKILLS_DIR.iterdir() if path.is_dir())


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


def check_plugin_version_rule(
    claude: dict[str, Any] | None,
    codex: dict[str, Any] | None,
    active_skills: list[Path],
    archived_skills: list[Path],
) -> CheckResult:
    """检查插件版本保持 0.<累计 skill 数>.<优化次数> 的仓库约定。"""

    result = CheckResult("Plugin version follows skill-count rule")
    expected_skill_count = len(active_skills) + len(archived_skills)

    for manifest_path, manifest in ((CLAUDE_MANIFEST, claude), (CODEX_MANIFEST, codex)):
        if manifest is None:
            result.details.append(f"Skipped {rel(manifest_path)} because it could not be loaded")
            continue

        version = manifest.get("version")
        if not isinstance(version, str):
            result.details.append(f"{rel(manifest_path)} field 'version' must be a string")
            continue

        match = PLUGIN_VERSION_RE.fullmatch(version)
        if not match:
            result.details.append(f"{rel(manifest_path)} version must use 0.<skill-count>.<iteration>")
            continue

        major, skill_count, _ = (int(part) for part in match.groups())
        if major != 0:
            # 本仓库不使用标准 SemVer Major 表达退役或 breaking change，避免丢失 skill 计数语义。
            result.details.append(f"{rel(manifest_path)} version major must remain 0, got {major}")
        if skill_count != expected_skill_count:
            # 退役目录保留历史 skill，因此活跃与退役目录之和就是累计新增数的确定性真源。
            result.details.append(
                f"{rel(manifest_path)} version skill count must be {expected_skill_count}, got {skill_count}"
            )

    return result


def check_hooks_object(value: Any, label: str) -> list[str]:
    """检查 hooks JSON / inline object 的最外层结构。"""

    if not isinstance(value, dict):
        return [f"{label} must be a JSON object"]
    hooks = value.get("hooks")
    if not isinstance(hooks, dict):
        return [f"{label} must contain a 'hooks' object"]
    return []


def check_hook_variable_scope(value: Any, label: str) -> list[str]:
    """检查 Claude / Codex hook 配置是否误用了对方的平台变量。"""

    text = stringify_for_check(value)
    details: list[str] = []
    if label == "hooks/hooks.json":
        if "${PLUGIN_ROOT}" in text:
            details.append(f"{label} is loaded by Claude Code and must not use Codex-only ${{PLUGIN_ROOT}}")
        if "skill-telemetry.py" in text and "${CLAUDE_PLUGIN_ROOT}" not in text:
            details.append(f"{label} telemetry command should use ${{CLAUDE_PLUGIN_ROOT}}")
    elif label == "hooks/codex-hooks.json":
        if "${CLAUDE_PLUGIN_ROOT}" in text:
            details.append(f"{label} is loaded by Codex and must not use Claude-only ${{CLAUDE_PLUGIN_ROOT}}")
        if "skill-telemetry.py" in text and "$HOME/.codex/hooks/iplugin-skill-telemetry.py" not in text:
            details.append(f"{label} telemetry command should use $HOME/.codex/hooks/iplugin-skill-telemetry.py")
        if "${PLUGIN_ROOT}/hooks/skill-telemetry.py" in text:
            details.append(f"{label} telemetry command must not use versioned ${{PLUGIN_ROOT}} cache path")
    return details


def stringify_for_check(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return str(value)


def check_hook_entry(result: CheckResult, entry: Any, label: str) -> None:
    if isinstance(entry, str):
        if not entry.startswith("./"):
            result.details.append(f"{label} path must start with './', got {entry!r}")
            return
        hook_path = (ROOT / entry).resolve()
        try:
            hook_path.relative_to(ROOT.resolve())
        except ValueError:
            result.details.append(f"{label} path must stay inside plugin root, got {entry!r}")
            return
        data, error = load_json(hook_path)
        if error:
            result.details.append(error)
            return
        hook_label = rel(hook_path)
        result.details.extend(check_hooks_object(data, hook_label))
        result.details.extend(check_hook_variable_scope(data, hook_label))
    elif isinstance(entry, dict):
        result.details.extend(check_hooks_object(entry, label))
        result.details.extend(check_hook_variable_scope(entry, label))
    else:
        result.details.append(f"{label} must be a './' path or inline hooks object")


def check_hooks_configs(codex: dict[str, Any] | None) -> CheckResult:
    """检查 Claude 默认 hooks 和 Codex manifest hooks 配置是否可加载。"""

    result = CheckResult("Hook configs are valid")

    default_hooks = HOOKS_DIR / "hooks.json"
    if not default_hooks.is_file():
        result.details.append(f"{rel(default_hooks)} does not exist")
    else:
        data, error = load_json(default_hooks)
        if error:
            result.details.append(error)
        else:
            label = rel(default_hooks)
            result.details.extend(check_hooks_object(data, label))
            result.details.extend(check_hook_variable_scope(data, label))

    if codex is None:
        result.details.append("Skipped Codex hooks because Codex manifest could not be loaded")
        return result

    hooks = codex.get("hooks")
    if hooks is None:
        result.details.append(f"{rel(CODEX_MANIFEST)} is missing 'hooks'")
        return result

    entries = hooks if isinstance(hooks, list) else [hooks]
    for index, entry in enumerate(entries):
        label = f"{rel(CODEX_MANIFEST)} hooks[{index}]"
        check_hook_entry(result, entry, label)
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


def extract_readme_deprecated_skill_names() -> tuple[set[str], list[str]]:
    """从 README 的 Deprecated Skills 表格中提取已退役名称。"""

    try:
        text = read_text(README)
    except FileNotFoundError:
        return set(), [f"{rel(README)} does not exist"]

    section_match = re.search(r"^## Deprecated Skills\s*$([\s\S]*?)(?=^## |\Z)", text, re.MULTILINE)
    if not section_match:
        return set(), [f"{rel(README)} is missing a '## Deprecated Skills' section"]

    names = set(re.findall(r"^\|\s*`([^`]+)`\s*\|", section_match.group(1), re.MULTILINE))
    if not names:
        return names, [f"{rel(README)} Deprecated Skills section has no archive rows"]
    return names, []


def extract_archive_index_skill_names() -> tuple[set[str], list[str]]:
    """读取归档目录自己的索引，保证退役原因不会只散落在根 README。"""

    try:
        text = read_text(DEPRECATED_SKILLS_README)
    except FileNotFoundError:
        return set(), [f"{rel(DEPRECATED_SKILLS_README)} does not exist"]

    names = set(re.findall(r"^\|\s*`([^`]+)`\s*\|", text, re.MULTILINE))
    if not names:
        return names, [f"{rel(DEPRECATED_SKILLS_README)} has no archive rows"]
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


def check_deprecated_skills(
    active_skills: list[Path],
    archived_skills: list[Path],
    claude: dict[str, Any] | None,
    codex: dict[str, Any] | None,
) -> CheckResult:
    """确保退役 skill 有自描述元数据，并与插件发现和当前能力声明隔离。"""

    result = CheckResult("Deprecated skills are isolated")
    if not DEPRECATED_SKILLS_DIR.is_dir():
        result.details.append(f"{rel(DEPRECATED_SKILLS_DIR)}/ does not exist")
        return result

    active_names = {path.name for path in active_skills}
    archived_names = {path.name for path in archived_skills}
    overlap = sorted(active_names & archived_names)
    if overlap:
        result.details.append(f"Skills cannot be active and deprecated at once: {', '.join(overlap)}")

    readme_active, active_errors = extract_readme_skill_names()
    readme_archived, archived_errors = extract_readme_deprecated_skill_names()
    archive_index, archive_index_errors = extract_archive_index_skill_names()
    result.details.extend(active_errors)
    result.details.extend(archived_errors)
    result.details.extend(archive_index_errors)
    leaked_active_rows = sorted(archived_names & readme_active)
    if leaked_active_rows:
        result.details.append(f"{rel(README)} active Skills table still lists: {', '.join(leaked_active_rows)}")
    missing_archive_rows = sorted(archived_names - readme_archived)
    extra_archive_rows = sorted(readme_archived - archived_names)
    if missing_archive_rows:
        result.details.append(f"{rel(README)} Deprecated Skills table is missing: {', '.join(missing_archive_rows)}")
    if extra_archive_rows:
        result.details.append(
            f"{rel(README)} Deprecated Skills table lists missing directories: {', '.join(extra_archive_rows)}"
        )
    missing_index_rows = sorted(archived_names - archive_index)
    extra_index_rows = sorted(archive_index - archived_names)
    if missing_index_rows:
        result.details.append(f"{rel(DEPRECATED_SKILLS_README)} is missing: {', '.join(missing_index_rows)}")
    if extra_index_rows:
        result.details.append(
            f"{rel(DEPRECATED_SKILLS_README)} lists missing directories: {', '.join(extra_index_rows)}"
        )

    for skill_dir in archived_skills:
        skill_file = skill_dir / "SKILL.md"
        data, error = parse_frontmatter(skill_file)
        if error:
            result.details.append(error)
            continue
        if data.get("name") != skill_dir.name:
            result.details.append(
                f"{rel(skill_file)} frontmatter name must be {skill_dir.name!r}, got {data.get('name')!r}"
            )
        if str(data.get("deprecated", "")).lower() != "true":
            result.details.append(f"{rel(skill_file)} must declare deprecated: true")
        for required in ("deprecated_in", "deprecated_reason"):
            if data.get(required) in (None, "", []):
                result.details.append(f"{rel(skill_file)} is missing non-empty field {required!r}")

    for manifest_path, manifest in ((CLAUDE_MANIFEST, claude), (CODEX_MANIFEST, codex)):
        if manifest is None:
            continue
        keywords = manifest.get("keywords", [])
        if isinstance(keywords, list):
            leaked_keywords = sorted(archived_names & {item for item in keywords if isinstance(item, str)})
            if leaked_keywords:
                result.details.append(
                    f"{rel(manifest_path)} keywords still register deprecated skills: {', '.join(leaked_keywords)}"
                )

    if codex is not None and codex.get("skills") != "./skills/":
        # 扫描根必须只指向活跃目录；扩大到仓库根会让归档 skill 再次进入可发现范围。
        result.details.append(f"{rel(CODEX_MANIFEST)} field 'skills' must be exactly './skills/'")

    return result


README_TREE_REQUIRED_TOP_LEVEL = {
    ".claude-plugin",
    ".codex-plugin",
    "skills",
    "deprecated-skills",
    "versions",
    "scripts",
    "git-hooks",
    "hooks",
    "tools",
    "CLAUDE.md",
    "AGENTS.md",
    "README.md",
    "CHANGELOG.md",
    ".gitignore",
}


def extract_readme_tree_top_level() -> tuple[set[str], list[str]]:
    """从 README 目录结构代码块中提取顶层路径。"""

    try:
        text = read_text(README)
    except FileNotFoundError:
        return set(), [f"{rel(README)} does not exist"]

    section_match = re.search(r"^## .*目录结构\s*$([\s\S]*?)(?=^## |\Z)", text, re.MULTILINE)
    if not section_match:
        return set(), [f"{rel(README)} is missing a directory structure section"]

    block_match = re.search(r"```(?:[A-Za-z0-9_-]+)?\n([\s\S]*?)```", section_match.group(1))
    if not block_match:
        return set(), [f"{rel(README)} directory structure section has no fenced tree"]

    entries: set[str] = set()
    for line in block_match.group(1).splitlines():
        match = re.match(r"^[├└]──\s+([^#]+)", line)
        if not match:
            continue
        entry = match.group(1).strip().rstrip("/")
        if entry and not entry.startswith("<"):
            entries.add(entry)

    return entries, []


def check_readme_directory_tree() -> CheckResult:
    """检查 README 目录结构代码块列出的核心顶层路径是否仍然存在。"""

    result = CheckResult("README directory tree matches repository")
    entries, errors = extract_readme_tree_top_level()
    result.details.extend(errors)
    if errors:
        return result

    missing_required = sorted(README_TREE_REQUIRED_TOP_LEVEL - entries)
    if missing_required:
        result.details.append(f"{rel(README)} directory tree is missing core entries: {', '.join(missing_required)}")

    for entry in sorted(entries):
        if not (ROOT / entry).exists():
            result.details.append(f"{rel(README)} directory tree lists missing path: {entry}")

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
    """检查 command 文件引用的 skill 存在，且 slash command 可由 command 或同名 skill 承载。"""

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
            if command_name not in commands and command_name not in skill_names:
                result.details.append(
                    f"{rel(scan_file)} mentions /{command_name}, but {rel(COMMANDS_DIR / (command_name + '.md'))} does not exist"
                )

    return result


def check_current_trigger_text(codex: dict[str, Any] | None) -> CheckResult:
    """检查当前触发文案是否和无独立 command 文件的约定一致。"""

    result = CheckResult("Current trigger text is consistent")

    html_report_files = [
        SKILLS_DIR / "html-report" / "SKILL.md",
        SKILLS_DIR / "html-report" / "references" / "content-rules.md",
    ]
    for path in html_report_files:
        if path.is_file() and "/htmlreport" in read_text(path):
            result.details.append(f"{rel(path)} should use /html-report instead of /htmlreport")

    best_of_web = SKILLS_DIR / "best-of-web" / "SKILL.md"
    if best_of_web.is_file() and "命令文件" in read_text(best_of_web):
        result.details.append(f"{rel(best_of_web)} should not reference removed command files")

    if codex is None:
        result.details.append("Skipped Codex defaultPrompt checks because Codex manifest could not be loaded")
        return result

    default_prompts = codex.get("interface", {}).get("defaultPrompt", [])
    if default_prompts and not isinstance(default_prompts, list):
        result.details.append(f"{rel(CODEX_MANIFEST)} interface.defaultPrompt must be a list when present")
        return result

    for prompt in default_prompts:
        if not isinstance(prompt, str):
            result.details.append(f"{rel(CODEX_MANIFEST)} interface.defaultPrompt entries must be strings")
            continue
        lower_prompt = prompt.lower()
        if (
            ("互联网上最优秀" in prompt or "best of web" in lower_prompt or "联网精选" in prompt)
            and not prompt.startswith("/best-of-web")
        ):
            result.details.append(
                f"{rel(CODEX_MANIFEST)} best-of-web defaultPrompt must start with /best-of-web: {prompt!r}"
            )
        if "/htmlreport" in prompt:
            result.details.append(f"{rel(CODEX_MANIFEST)} defaultPrompt should use /html-report: {prompt!r}")

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


def check_skill_evals(skills: list[Path]) -> CheckResult:
    """校验 skill 自带 evals.json 的基础结构和 fixture 路径。

    eval 回归集是面向质量退化的人工/半自动护栏；这里不尝试运行模型，只确保
    用例定义可读、关键字段齐全、引用的 fixture 没有断链，避免后续维护时悄悄失效。
    """

    result = CheckResult("Skill eval fixtures are valid")
    for skill_dir in skills:
        evals_path = skill_dir / EVALS_RELATIVE_PATH
        if not evals_path.is_file():
            continue

        data, error = load_json(evals_path)
        if error:
            result.details.append(error)
            continue
        if not isinstance(data, dict):
            result.details.append(f"{rel(evals_path)} must contain a JSON object")
            continue

        skill_name = data.get("skill_name")
        if skill_name != skill_dir.name:
            result.details.append(
                f"{rel(evals_path)} skill_name must match directory name {skill_dir.name!r}"
            )

        evals = data.get("evals")
        if not isinstance(evals, list) or not evals:
            result.details.append(f"{rel(evals_path)} must contain a non-empty evals array")
            continue

        seen_ids: set[int] = set()
        for index, item in enumerate(evals, start=1):
            label = f"{rel(evals_path)} eval #{index}"
            if not isinstance(item, dict):
                result.details.append(f"{label} must be an object")
                continue

            eval_id = item.get("id")
            if not isinstance(eval_id, int):
                result.details.append(f"{label} id must be an integer")
            elif eval_id in seen_ids:
                result.details.append(f"{label} id {eval_id} is duplicated")
            else:
                seen_ids.add(eval_id)

            for field_name in ("prompt", "expected_output"):
                if not isinstance(item.get(field_name), str) or not item[field_name].strip():
                    result.details.append(f"{label} {field_name} must be a non-empty string")

            expectations = item.get("expectations")
            if not isinstance(expectations, list) or not expectations:
                result.details.append(f"{label} expectations must be a non-empty string array")
            elif not all(isinstance(expectation, str) and expectation.strip() for expectation in expectations):
                result.details.append(f"{label} expectations must only contain non-empty strings")

            files = item.get("files", [])
            if not isinstance(files, list):
                result.details.append(f"{label} files must be an array when present")
                continue
            for file_ref in files:
                if not isinstance(file_ref, str) or not file_ref.strip():
                    result.details.append(f"{label} files must only contain non-empty strings")
                    continue
                # 文件引用统一相对 skill 根目录，保证 eval 目录移动或被复制时语义稳定。
                if Path(file_ref).is_absolute() or ".." in Path(file_ref).parts:
                    result.details.append(f"{label} file path must be relative inside the skill: {file_ref}")
                    continue
                if not (skill_dir / file_ref).is_file():
                    result.details.append(f"{label} referenced fixture does not exist: {file_ref}")

    return result


def check_html_report_annotation_assets() -> CheckResult:
    """检查 html-report 批注模式资产是否保留剥离 marker 和路径元数据占位符。

    批注资产最终会被注入到单文件 HTML 中，marker 是重复注入清理和导出发布版
    物理剥离的边界；`__QA_REPORT_META__` 则保护内嵌审核包和 Markdown 能回查来源。
    """

    result = CheckResult("HTML report annotation assets are valid")
    for path, required_fragments in HTML_REPORT_ANNOTATION_ASSETS.items():
        if not path.is_file():
            result.details.append(f"{rel(path)} does not exist")
            continue

        text = read_text(path)
        for fragment in required_fragments:
            if fragment not in text:
                result.details.append(f"{rel(path)} is missing {fragment}")

        if path.name == "annotation.js" and text.count("</script>") != 1:
            # 资产自身就是 inline script；注释或字符串出现结束标签也会让浏览器提前截断脚本。
            result.details.append(f"{rel(path)} must contain exactly one literal </script> wrapper closing tag")

    return result


def check_html_report_review_workspace_assets() -> CheckResult:
    """检查多版本审阅组件的 runtime、CSS 和构建脚本仍保持配套契约。

    Workspace 的 JSON 会把静态高亮源码交给 runtime 写入 innerHTML，因此构建脚本的
    raw-text 转义、runtime 完整性标记和 CSS 关键结构必须一起存在，不能只发布其中一部分。
    """

    result = CheckResult("HTML report Review Workspace assets are valid")
    for path, required_fragments in HTML_REPORT_REVIEW_WORKSPACE_ASSETS.items():
        if not path.is_file():
            result.details.append(f"{rel(path)} does not exist")
            continue

        text = read_text(path)
        for fragment in required_fragments:
            if fragment not in text:
                result.details.append(f"{rel(path)} is missing {fragment}")

        if path.name == "workspace.js" and "</script>" in text.lower():
            # runtime 会被原样包进 inline script，任何字面结束标签都会让浏览器提前截断。
            result.details.append(f"{rel(path)} must not contain a literal </script>")

    return result


def check_html_report_component_assets() -> CheckResult:
    """检查组件注册表、依赖和资产完整性，保证装配器输入是一致的单一真源。"""

    result = CheckResult("HTML report component assets are valid")
    registry, error = load_json(HTML_REPORT_COMPONENT_REGISTRY)
    if error:
        result.details.append(error)
        return result
    if not isinstance(registry, dict) or registry.get("schemaVersion") != 1:
        result.details.append(f"{rel(HTML_REPORT_COMPONENT_REGISTRY)} schemaVersion must be 1")
        return result

    components = registry.get("components")
    defaults = registry.get("defaults")
    if not isinstance(components, dict) or not components:
        result.details.append(f"{rel(HTML_REPORT_COMPONENT_REGISTRY)} components must be a non-empty object")
        return result
    if not isinstance(defaults, list) or not all(isinstance(name, str) for name in defaults):
        result.details.append(f"{rel(HTML_REPORT_COMPONENT_REGISTRY)} defaults must be a string array")
        defaults = []

    for name in defaults:
        if name not in components:
            result.details.append(f"{rel(HTML_REPORT_COMPONENT_REGISTRY)} default component is missing: {name}")

    skill_root = SKILLS_DIR / "html-report"
    for name, component in components.items():
        label = f"{rel(HTML_REPORT_COMPONENT_REGISTRY)} component {name}"
        if not isinstance(component, dict):
            result.details.append(f"{label} must be an object")
            continue

        dependencies = component.get("dependencies")
        if not isinstance(dependencies, list) or not all(isinstance(item, str) for item in dependencies):
            result.details.append(f"{label} dependencies must be a string array")
            dependencies = []
        for dependency in dependencies:
            if dependency not in components:
                result.details.append(f"{label} references missing dependency {dependency}")

        for asset_type, suffix in (("styles", "style"), ("scripts", "script")):
            assets = component.get(asset_type)
            if not isinstance(assets, list) or not all(isinstance(item, str) for item in assets):
                result.details.append(f"{label} {asset_type} must be a string array")
                continue
            for asset in assets:
                asset_path = (HTML_REPORT_COMPONENT_ROOT / asset).resolve()
                try:
                    asset_path.relative_to(skill_root.resolve())
                except ValueError:
                    result.details.append(f"{label} {suffix} escapes html-report: {asset}")
                    continue
                if not asset_path.is_file():
                    result.details.append(f"{label} {suffix} does not exist: {asset}")
                    continue
                source = read_text(asset_path)
                closing_tag = f"</{suffix}>"
                if closing_tag in source.lower():
                    result.details.append(f"{rel(asset_path)} must not contain literal {closing_tag}")
                if asset_type == "scripts":
                    marker_name = name.replace("-", "_").upper()
                    for marker_suffix in ("START", "END"):
                        marker = f"HTML_REPORT_{marker_name}_RUNTIME_{marker_suffix}"
                        if marker not in source:
                            result.details.append(f"{rel(asset_path)} is missing {marker}")

    for path, fragments in {
        SKILLS_DIR / "html-report" / "scripts" / "assemble_report.py": (
            "REGISTRY_PATH",
            "resolve_components",
            "data-html-report-components",
            "data-html-report-runtime",
        ),
        SKILLS_DIR / "html-report" / "scripts" / "check_html_report.py": (
            "registry.json",
            "check_component_bundle",
            "check_behavior_component_markup",
            "check_file_location_links",
        ),
    }.items():
        if not path.is_file():
            result.details.append(f"{rel(path)} does not exist")
            continue
        source = read_text(path)
        for fragment in fragments:
            if fragment not in source:
                result.details.append(f"{rel(path)} is missing {fragment}")

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
    archived_skills = deprecated_skill_dirs()
    skill_names = {path.name for path in skills}
    frontmatter_result, _ = check_skills_frontmatter(skills)

    results = [
        json_result,
        check_manifest_common_fields(claude_manifest, codex_manifest),
        check_plugin_version_rule(claude_manifest, codex_manifest, skills, archived_skills),
        check_hooks_configs(codex_manifest),
        frontmatter_result,
        check_readme_directory_tree(),
        check_readme_skills(skills),
        check_deprecated_skills(skills, archived_skills, claude_manifest, codex_manifest),
        check_manifest_keywords(claude_manifest, codex_manifest, skills),
        check_changelog_versions(),
        check_commands(skill_names),
        check_current_trigger_text(codex_manifest),
        check_claude_agents_sync(),
        check_no_hardcoded_homedir(skills),
        check_skill_evals(skills),
        check_html_report_annotation_assets(),
        check_html_report_component_assets(),
        check_html_report_review_workspace_assets(),
    ]

    print_results(results)
    return 1 if any(not result.passed for result in results) else 0


if __name__ == "__main__":
    sys.exit(main())
