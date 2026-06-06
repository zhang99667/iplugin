#!/usr/bin/env python3
"""为 html-report 生成已转义、轻量高亮的代码块 HTML。

目标是确定性和安全性，不追求完整语法高亮。脚本会先转义所有源码文本，
再把已知 token 包成 html-report 模板里的 CSS class。
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path


SUPPORTED_LANGS = {"kotlin", "java", "js", "python", "xml", "sql", "json", "yaml", "bash", "diff", "text"}

# 让常见文件后缀或语言别名映射到模板支持的语言名。
LANG_ALIASES = {
    "kt": "kotlin",
    "kts": "kotlin",
    "javascript": "js",
    "jsx": "js",
    "ts": "js",
    "tsx": "js",
    "py": "python",
    "html": "xml",
    "xhtml": "xml",
    "svg": "xml",
    "mysql": "sql",
    "hive": "sql",
    "spark": "sql",
    "jsonc": "json",
    "yml": "yaml",
    "conf": "yaml",
    "config": "yaml",
    "properties": "yaml",
    "shell": "bash",
    "sh": "bash",
    "zsh": "bash",
    "patch": "diff",
}

KEYWORDS = {
    "kotlin": {
        "as",
        "break",
        "by",
        "catch",
        "class",
        "companion",
        "continue",
        "data",
        "do",
        "else",
        "enum",
        "false",
        "finally",
        "for",
        "fun",
        "if",
        "import",
        "in",
        "interface",
        "internal",
        "is",
        "null",
        "object",
        "open",
        "override",
        "package",
        "private",
        "protected",
        "public",
        "return",
        "sealed",
        "super",
        "this",
        "throw",
        "true",
        "try",
        "typealias",
        "val",
        "var",
        "when",
        "while",
    },
    "java": {
        "abstract",
        "assert",
        "boolean",
        "break",
        "byte",
        "case",
        "catch",
        "char",
        "class",
        "const",
        "continue",
        "default",
        "do",
        "double",
        "else",
        "enum",
        "extends",
        "false",
        "final",
        "finally",
        "float",
        "for",
        "if",
        "implements",
        "import",
        "instanceof",
        "int",
        "interface",
        "long",
        "native",
        "new",
        "null",
        "package",
        "private",
        "protected",
        "public",
        "return",
        "short",
        "static",
        "strictfp",
        "super",
        "switch",
        "synchronized",
        "this",
        "throw",
        "throws",
        "transient",
        "true",
        "try",
        "void",
        "volatile",
        "while",
    },
    "js": {
        "await",
        "break",
        "case",
        "catch",
        "class",
        "const",
        "continue",
        "debugger",
        "default",
        "delete",
        "do",
        "else",
        "export",
        "extends",
        "false",
        "finally",
        "for",
        "from",
        "function",
        "if",
        "import",
        "in",
        "instanceof",
        "let",
        "new",
        "null",
        "of",
        "return",
        "super",
        "switch",
        "this",
        "throw",
        "true",
        "try",
        "typeof",
        "undefined",
        "var",
        "void",
        "while",
        "yield",
    },
    "python": {
        "and",
        "as",
        "assert",
        "async",
        "await",
        "break",
        "class",
        "continue",
        "def",
        "del",
        "elif",
        "else",
        "except",
        "False",
        "finally",
        "for",
        "from",
        "global",
        "if",
        "import",
        "in",
        "is",
        "lambda",
        "None",
        "nonlocal",
        "not",
        "or",
        "pass",
        "raise",
        "return",
        "True",
        "try",
        "while",
        "with",
        "yield",
    },
    "sql": {
        "ADD",
        "ALTER",
        "AND",
        "AS",
        "ASC",
        "BETWEEN",
        "BY",
        "CASE",
        "CAST",
        "COUNT",
        "CREATE",
        "CROSS",
        "DELETE",
        "DESC",
        "DISTINCT",
        "DROP",
        "ELSE",
        "END",
        "FROM",
        "FULL",
        "GROUP",
        "HAVING",
        "IF",
        "IN",
        "INNER",
        "INSERT",
        "INTO",
        "IS",
        "JOIN",
        "LEFT",
        "LIKE",
        "LIMIT",
        "NOT",
        "NULL",
        "ON",
        "OR",
        "ORDER",
        "OUTER",
        "OVER",
        "PARTITION",
        "RIGHT",
        "SELECT",
        "SET",
        "SUM",
        "THEN",
        "UNION",
        "UPDATE",
        "VALUES",
        "WHEN",
        "WHERE",
        "WITH",
    },
    "json": {"true", "false", "null"},
    "bash": {
        "case",
        "do",
        "done",
        "elif",
        "else",
        "esac",
        "fi",
        "for",
        "function",
        "if",
        "in",
        "then",
        "until",
        "while",
    },
}

TYPES = {
    "kotlin": {"Any", "Boolean", "Byte", "Char", "Double", "Float", "Int", "Long", "Short", "String", "Unit"},
    "java": {"Boolean", "Byte", "Character", "Double", "Float", "Integer", "Long", "Object", "Short", "String", "Void"},
    "js": {"Array", "BigInt", "Boolean", "Date", "Map", "Number", "Object", "Promise", "Set", "String", "Symbol"},
    "python": {"bool", "bytes", "dict", "float", "int", "list", "object", "set", "str", "tuple"},
}


def css_span(class_name: str, text: str) -> str:
    return f'<span class="{class_name}">{html.escape(text)}</span>'


def normalize_lang(lang: str) -> str:
    normalized = lang.lower().strip()
    normalized = LANG_ALIASES.get(normalized, normalized)
    if normalized not in SUPPORTED_LANGS:
        raise SystemExit(f"Unsupported language: {lang}. Supported: {', '.join(sorted(SUPPORTED_LANGS))}")
    return normalized


def read_source(path: str | None) -> str:
    if not path or path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def token_pattern(lang: str) -> re.Pattern[str]:
    """按语言返回一个保守 token 正则，避免过度解析。"""

    if lang == "python":
        comment = r"#[^\n]*"
        string = r"'''[\s\S]*?'''|\"\"\"[\s\S]*?\"\"\"|(?:r|R|f|F|fr|FR|rf|RF)?'(?:\\.|[^'\\])*'|(?:r|R|f|F|fr|FR|rf|RF)?\"(?:\\.|[^\"\\])*\""
    elif lang == "bash":
        comment = r"#[^\n]*"
        string = r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`'
    elif lang == "sql":
        comment = r"--[^\n]*|/\*[\s\S]*?\*/"
        string = r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`'
    elif lang == "json":
        comment = r"(?!)"
        string = r'"(?:\\.|[^"\\])*"'
    else:
        comment = r"//[^\n]*|/\*[\s\S]*?\*/"
        string = r'"""[\s\S]*?"""|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`'
    number = r"\b(?:0[xX][0-9A-Fa-f_]+|\d[\d_]*(?:\.\d[\d_]*)?(?:[eE][+-]?\d[\d_]*)?[fFdDlL]?)\b"
    word = r"\b[A-Za-z_][A-Za-z0-9_]*\b"
    return re.compile(
        rf"(?P<comment>{comment})|(?P<string>{string})|(?P<number>{number})|(?P<word>{word})",
        re.MULTILINE,
    )


def next_nonspace(source: str, index: int) -> str:
    while index < len(source) and source[index].isspace():
        index += 1
    return source[index] if index < len(source) else ""


def highlight_general(source: str, lang: str) -> str:
    """高亮 Kotlin/Java/JS/Python 这类 C-like 或常规语言片段。"""

    pattern = token_pattern(lang)
    pieces: list[str] = []
    last = 0
    keywords = KEYWORDS.get(lang, set())
    types = TYPES.get(lang, set())

    for match in pattern.finditer(source):
        pieces.append(html.escape(source[last : match.start()]))
        text = match.group(0)
        kind = match.lastgroup
        keyword_text = text.upper() if lang == "sql" else text
        if kind == "comment":
            pieces.append(css_span("tok-cmt", text))
        elif kind == "string":
            pieces.append(css_span("tok-str", text))
        elif kind == "number":
            pieces.append(css_span("tok-num", text))
        elif keyword_text in keywords:
            pieces.append(css_span("tok-key", text))
        elif text in types:
            pieces.append(css_span("tok-type", text))
        elif next_nonspace(source, match.end()) == "(":
            pieces.append(css_span("tok-fn", text))
        else:
            pieces.append(html.escape(text))
        last = match.end()

    pieces.append(html.escape(source[last:]))
    return "".join(pieces)


YAML_KEY_RE = re.compile(r"^(\s*)([A-Za-z0-9_.-]+)(\s*:)", re.MULTILINE)


def highlight_yaml(source: str) -> str:
    """高亮 YAML/配置片段里的 key、注释、字符串和数字。"""

    pieces: list[str] = []
    last = 0
    for match in YAML_KEY_RE.finditer(source):
        pieces.append(html.escape(source[last : match.start()]))
        pieces.append(html.escape(match.group(1)))
        pieces.append(css_span("tok-var", match.group(2)))
        pieces.append(html.escape(match.group(3)))
        last = match.end()

    tail = html.escape(source[last:])
    tail = re.sub(r"(#.*)$", lambda m: css_span("tok-cmt", html.unescape(m.group(1))), tail, flags=re.MULTILINE)
    pieces.append(tail)
    return "".join(pieces)


def highlight_bash(source: str) -> str:
    """高亮 shell 片段，并把每行第一个命令标成函数 token。"""

    pieces: list[str] = []
    for line in source.splitlines(keepends=True):
        newline = "\n" if line.endswith("\n") else ""
        body = line[:-1] if newline else line
        stripped = body.lstrip()
        if not stripped:
            pieces.append(html.escape(body) + newline)
            continue
        if stripped.startswith("#"):
            pieces.append(css_span("tok-cmt", body) + newline)
            continue

        match = re.match(r"(\s*)([A-Za-z0-9_./:-]+)([\s\S]*)", body)
        if not match:
            pieces.append(highlight_general(body, "bash") + newline)
            continue

        indent, command, rest = match.groups()
        command_class = "tok-key" if command in KEYWORDS["bash"] else "tok-fn"
        pieces.append(html.escape(indent))
        pieces.append(css_span(command_class, command))
        pieces.append(highlight_general(rest, "bash"))
        pieces.append(newline)
    return "".join(pieces)


def highlight_diff(source: str) -> str:
    """高亮 unified diff，保留行首 +/- 作为视觉锚点。"""

    pieces: list[str] = []
    lines = source.splitlines(keepends=True)
    for line in lines:
        body = line[:-1] if line.endswith("\n") else line
        newline = "\n" if line.endswith("\n") else ""
        escaped = html.escape(body)
        if body.startswith("@@") or body.startswith("diff ") or body.startswith("index ") or body.startswith("+++") or body.startswith("---"):
            pieces.append(f'<span class="tok-cmt">{escaped}</span>{newline}')
        elif body.startswith("+"):
            pieces.append(f'<span class="tok-add">{escaped}</span>{newline}')
        elif body.startswith("-"):
            pieces.append(f'<span class="tok-del">{escaped}</span>{newline}')
        else:
            pieces.append(f"{escaped}{newline}")
    return "".join(pieces)


HUNK_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def render_diff_row(row_class: str, marker: str, old_num: int | None, new_num: int | None, code: str) -> str:
    """生成一行带 old/new 行号的 diff viewer 表格。"""

    old_text = str(old_num) if old_num is not None else ""
    new_text = str(new_num) if new_num is not None else ""
    return (
        f'    <tr class="diff-line {row_class}">'
        f'<td class="diff-gutter">{html.escape(marker)}</td>'
        f'<td class="diff-num diff-old-num">{old_text}</td>'
        f'<td class="diff-num diff-new-num">{new_text}</td>'
        f'<td class="diff-code">{html.escape(code)}</td>'
        "</tr>"
    )


def render_diff_note(row_class: str, code: str) -> str:
    """生成 hunk header、文件头或 diff 元信息行。"""

    return (
        f'    <tr class="diff-line {row_class}">'
        '<td class="diff-gutter"></td>'
        '<td class="diff-num diff-old-num"></td>'
        '<td class="diff-num diff-new-num"></td>'
        f'<td class="diff-code">{html.escape(code)}</td>'
        "</tr>"
    )


def render_diff_viewer(source: str) -> str:
    """把 unified diff 渲染成类似代码评审工具的静态 HTML 视图。"""

    rows: list[str] = []
    old_line: int | None = None
    new_line: int | None = None

    for line in source.splitlines():
        hunk = HUNK_RE.match(line)
        if hunk:
            old_line = int(hunk.group(1))
            new_line = int(hunk.group(2))
            rows.append(render_diff_note("diff-hunk", line))
            continue

        if line.startswith(("diff ", "index ", "--- ", "+++ ")):
            rows.append(render_diff_note("diff-meta", line))
            continue

        if line.startswith("\\"):
            rows.append(render_diff_note("diff-meta", line))
            continue

        if line.startswith("-") and old_line is not None:
            rows.append(render_diff_row("diff-del", "-", old_line, None, line[1:]))
            old_line += 1
            continue

        if line.startswith("+") and new_line is not None:
            rows.append(render_diff_row("diff-add", "+", None, new_line, line[1:]))
            new_line += 1
            continue

        if line.startswith(" ") and old_line is not None and new_line is not None:
            rows.append(render_diff_row("diff-context", "", old_line, new_line, line[1:]))
            old_line += 1
            new_line += 1
            continue

        rows.append(render_diff_note("diff-meta", line))

    if not rows:
        rows.append(render_diff_note("diff-meta", ""))

    return (
        '<section class="diff-card diff-viewer">\n'
        '  <div class="diff-header">\n'
        '    <span class="change-chip change-mod">Diff</span>\n'
        '    <span class="muted">Unified diff viewer</span>\n'
        "  </div>\n"
        '  <div class="diff-scroll">\n'
        '  <table class="diff-table" aria-label="代码差异">\n'
        "    <tbody>\n"
        + "\n".join(rows)
        + "\n"
        "    </tbody>\n"
        "  </table>\n"
        "  </div>\n"
        "</section>"
    )


XML_TOKEN_RE = re.compile(r"<!--[\s\S]*?-->|<[^>]+>")
XML_ATTR_RE = re.compile(r"([A-Za-z_:][\w:.-]*)(\s*=\s*)(\"[^\"]*\"|'[^']*')")


def highlight_xml_tag(tag: str) -> str:
    """高亮单个 XML/HTML 标签，属性名和属性值分开标记。"""

    if tag.startswith("<!--"):
        return css_span("tok-cmt", tag)

    match = re.match(r"(</?)([A-Za-z_:][\w:.-]*)([\s\S]*?)(/?>)$", tag)
    if not match:
        return html.escape(tag)

    opener, name, attrs, closer = match.groups()
    pieces = [css_span("tok-key", opener + name)]
    last = 0
    for attr in XML_ATTR_RE.finditer(attrs):
        pieces.append(html.escape(attrs[last : attr.start()]))
        pieces.append(css_span("tok-var", attr.group(1)))
        pieces.append(html.escape(attr.group(2)))
        pieces.append(css_span("tok-str", attr.group(3)))
        last = attr.end()
    pieces.append(html.escape(attrs[last:]))
    pieces.append(css_span("tok-key", closer))
    return "".join(pieces)


def highlight_xml(source: str) -> str:
    """高亮 XML/HTML 文本，其余普通文本只做 HTML 转义。"""

    pieces: list[str] = []
    last = 0
    for match in XML_TOKEN_RE.finditer(source):
        pieces.append(html.escape(source[last : match.start()]))
        pieces.append(highlight_xml_tag(match.group(0)))
        last = match.end()
    pieces.append(html.escape(source[last:]))
    return "".join(pieces)


def highlight(source: str, lang: str) -> str:
    if lang == "text":
        return html.escape(source)
    if lang == "diff":
        return highlight_diff(source)
    if lang == "xml":
        return highlight_xml(source)
    if lang == "yaml":
        return highlight_yaml(source)
    if lang == "bash":
        return highlight_bash(source)
    return highlight_general(source, lang)


def can_use_pygments() -> bool:
    """检查当前环境是否可用 Pygments，不触发安装或联网。"""

    return importlib.util.find_spec("pygments") is not None or shutil.which("pygmentize") is not None


def pygments_lexer_name(lang: str) -> str:
    return {
        "js": "javascript",
        "xml": "html",
        "yaml": "yaml",
        "bash": "bash",
    }.get(lang, lang)


def highlight_pygments(source: str, lang: str) -> str:
    """使用本地 Pygments 生成静态 HTML；不可用时由调用方回退。"""

    lexer_name = pygments_lexer_name(lang)
    if importlib.util.find_spec("pygments") is None:
        return highlight_pygmentize(source, lexer_name)

    from pygments import highlight as pygments_highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import get_lexer_by_name
    from pygments.util import ClassNotFound

    try:
        lexer = get_lexer_by_name(lexer_name)
    except ClassNotFound:
        lexer = get_lexer_by_name("text")

    formatter = HtmlFormatter(nowrap=True, noclasses=True, style="monokai")
    return pygments_highlight(source, lexer, formatter)


def highlight_pygmentize(source: str, lexer_name: str) -> str:
    """使用 pygmentize CLI 作为 Pygments 模块不可导入时的本地后备。"""

    command = [
        "pygmentize",
        "-f",
        "html",
        "-l",
        lexer_name,
        "-O",
        "nowrap=True,noclasses=True,style=monokai",
    ]
    try:
        result = subprocess.run(command, input=source, text=True, capture_output=True, check=True)
    except subprocess.CalledProcessError:
        fallback = command.copy()
        fallback[4] = "text"
        result = subprocess.run(fallback, input=source, text=True, capture_output=True, check=True)
    return result.stdout


def select_engine(requested: str, lang: str, mode: str) -> str:
    """选择高亮引擎。默认 builtin；增强引擎只用于普通代码块。"""

    if mode != "code" or lang in {"text", "diff"}:
        return "builtin"
    if requested == "builtin":
        return "builtin"
    if requested == "pygments":
        if not can_use_pygments():
            raise SystemExit("--engine pygments 需要本机 Python 环境已安装 Pygments")
        return "pygments"
    if requested == "auto":
        return "pygments" if can_use_pygments() else "builtin"
    raise SystemExit(f"Unsupported engine: {requested}")


def highlight_with_engine(source: str, lang: str, engine: str) -> str:
    if engine == "pygments":
        return highlight_pygments(source, lang)
    return highlight(source, lang)


def render_code_wrap(source: str, lang: str, copy_button: bool = True, engine: str = "builtin") -> str:
    """输出可直接嵌入报告正文的 .code-wrap 片段。"""

    highlighted = highlight_with_engine(source, lang, engine)
    button = '\n  <button class="copy-btn" type="button" aria-label="复制代码">复制</button>' if copy_button else ""
    return (
        '<div class="code-wrap">\n'
        f'  <pre><code class="language-{lang}">{highlighted}</code></pre>'
        f"{button}\n"
        "</div>"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成已转义、轻量高亮的 HTML 代码块。")
    parser.add_argument("input", nargs="?", help="输入文件路径；省略或传 '-' 时从 stdin 读取。")
    parser.add_argument("--lang", required=True, help="语言：kotlin、java、js、python、xml、sql、json、yaml、bash、diff 或 text。")
    parser.add_argument("--mode", choices=["code", "diff-viewer"], default="code", help="输出模式；diff-viewer 用于带 old/new 行号的差异视图。")
    parser.add_argument("--diff-view", action="store_true", help="等同于 --mode diff-viewer，仅支持 --lang diff。")
    parser.add_argument("--engine", choices=["builtin", "auto", "pygments"], default="builtin", help="高亮引擎：builtin 为零依赖默认值；auto/pygments 可使用本机 Pygments 预渲染。")
    parser.add_argument("--no-copy", action="store_true", help="不生成复制按钮。")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    lang = normalize_lang(args.lang)
    source = read_source(args.input)
    mode = "diff-viewer" if args.diff_view else args.mode
    if mode == "diff-viewer":
        if lang != "diff":
            raise SystemExit("--mode diff-viewer 只支持 --lang diff")
        sys.stdout.write(render_diff_viewer(source))
    else:
        engine = select_engine(args.engine, lang, mode)
        sys.stdout.write(render_code_wrap(source, lang, copy_button=not args.no_copy, engine=engine))
    if source and not source.endswith("\n"):
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
