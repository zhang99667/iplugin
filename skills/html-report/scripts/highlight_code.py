#!/usr/bin/env python3
"""为 html-report 生成已转义、轻量高亮的代码块 HTML。

目标是确定性和安全性，不追求完整语法高亮。脚本会先转义所有源码文本，
再把已知 token 包成 html-report 模板里的 CSS class。
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


SUPPORTED_LANGS = {
    "bash",
    "c",
    "cpp",
    "diff",
    "go",
    "ini",
    "java",
    "js",
    "json",
    "kotlin",
    "markdown",
    "objc",
    "php",
    "python",
    "ruby",
    "rust",
    "sql",
    "swift",
    "toml",
    "ts",
    "text",
    "xml",
    "yaml",
}

# 让常见文件后缀或语言别名映射到模板支持的语言名。
LANG_ALIASES = {
    "kt": "kotlin",
    "kts": "kotlin",
    "javascript": "js",
    "jsx": "js",
    "typescript": "ts",
    "tsx": "ts",
    "c++": "cpp",
    "cc": "cpp",
    "cxx": "cpp",
    "hpp": "cpp",
    "hh": "cpp",
    "hxx": "cpp",
    "objective-c": "objc",
    "objectivec": "objc",
    "obj-c": "objc",
    "objective-c++": "objc",
    "obj-c++": "objc",
    "m": "objc",
    "mm": "objc",
    "h": "objc",
    "rs": "rust",
    "rb": "ruby",
    "md": "markdown",
    "mkd": "markdown",
    "mdown": "markdown",
    "py": "python",
    "html": "xml",
    "xhtml": "xml",
    "svg": "xml",
    "mysql": "sql",
    "hive": "sql",
    "spark": "sql",
    "jsonc": "json",
    "yml": "yaml",
    "tml": "toml",
    "cfg": "ini",
    "conf": "yaml",
    "config": "yaml",
    "properties": "yaml",
    "plist": "xml",
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
    "c": {
        "auto",
        "break",
        "case",
        "char",
        "const",
        "continue",
        "default",
        "do",
        "double",
        "else",
        "enum",
        "extern",
        "false",
        "float",
        "for",
        "goto",
        "if",
        "inline",
        "int",
        "long",
        "NULL",
        "register",
        "restrict",
        "return",
        "short",
        "signed",
        "sizeof",
        "static",
        "struct",
        "switch",
        "true",
        "typedef",
        "union",
        "unsigned",
        "void",
        "volatile",
        "while",
    },
    "cpp": {
        "alignas",
        "alignof",
        "and",
        "asm",
        "auto",
        "bool",
        "break",
        "case",
        "catch",
        "char",
        "char16_t",
        "char32_t",
        "class",
        "const",
        "constexpr",
        "const_cast",
        "continue",
        "decltype",
        "default",
        "delete",
        "do",
        "double",
        "dynamic_cast",
        "else",
        "enum",
        "explicit",
        "export",
        "extern",
        "false",
        "float",
        "for",
        "friend",
        "goto",
        "if",
        "inline",
        "int",
        "long",
        "mutable",
        "namespace",
        "new",
        "noexcept",
        "nullptr",
        "operator",
        "private",
        "protected",
        "public",
        "register",
        "reinterpret_cast",
        "return",
        "short",
        "signed",
        "sizeof",
        "static",
        "static_assert",
        "static_cast",
        "struct",
        "switch",
        "template",
        "this",
        "thread_local",
        "throw",
        "true",
        "try",
        "typedef",
        "typeid",
        "typename",
        "union",
        "unsigned",
        "using",
        "virtual",
        "void",
        "volatile",
        "while",
    },
    "objc": {
        "assign",
        "atomic",
        "autoreleasepool",
        "BOOL",
        "break",
        "case",
        "catch",
        "char",
        "class",
        "const",
        "continue",
        "copy",
        "default",
        "do",
        "double",
        "dynamic",
        "else",
        "end",
        "enum",
        "false",
        "finally",
        "float",
        "for",
        "FOUNDATION_EXPORT",
        "if",
        "implementation",
        "import",
        "instancetype",
        "int",
        "interface",
        "long",
        "nil",
        "Nil",
        "NO",
        "nonatomic",
        "nonnull",
        "nullable",
        "NULL",
        "optional",
        "package",
        "private",
        "property",
        "protected",
        "protocol",
        "public",
        "readonly",
        "readwrite",
        "required",
        "retain",
        "return",
        "selector",
        "self",
        "short",
        "signed",
        "sizeof",
        "static",
        "strong",
        "struct",
        "super",
        "switch",
        "synthesize",
        "throw",
        "true",
        "try",
        "typedef",
        "union",
        "unsigned",
        "void",
        "volatile",
        "weak",
        "while",
        "YES",
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
    "ts": {
        "abstract",
        "any",
        "as",
        "async",
        "await",
        "boolean",
        "break",
        "case",
        "catch",
        "class",
        "const",
        "constructor",
        "continue",
        "debugger",
        "declare",
        "default",
        "delete",
        "do",
        "else",
        "enum",
        "export",
        "extends",
        "false",
        "finally",
        "for",
        "from",
        "function",
        "get",
        "if",
        "implements",
        "import",
        "in",
        "infer",
        "instanceof",
        "interface",
        "keyof",
        "let",
        "module",
        "namespace",
        "never",
        "new",
        "null",
        "number",
        "of",
        "private",
        "protected",
        "public",
        "readonly",
        "return",
        "set",
        "string",
        "super",
        "switch",
        "symbol",
        "this",
        "throw",
        "true",
        "try",
        "type",
        "typeof",
        "undefined",
        "unknown",
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
    "swift": {
        "Any",
        "as",
        "associatedtype",
        "break",
        "case",
        "catch",
        "class",
        "continue",
        "defer",
        "deinit",
        "do",
        "else",
        "enum",
        "extension",
        "false",
        "fileprivate",
        "for",
        "func",
        "guard",
        "if",
        "import",
        "in",
        "init",
        "inout",
        "internal",
        "is",
        "let",
        "nil",
        "open",
        "operator",
        "private",
        "protocol",
        "public",
        "repeat",
        "return",
        "self",
        "Self",
        "static",
        "struct",
        "subscript",
        "super",
        "switch",
        "throw",
        "throws",
        "true",
        "try",
        "typealias",
        "var",
        "where",
        "while",
    },
    "go": {
        "break",
        "case",
        "chan",
        "const",
        "continue",
        "default",
        "defer",
        "else",
        "fallthrough",
        "false",
        "for",
        "func",
        "go",
        "goto",
        "if",
        "import",
        "interface",
        "map",
        "nil",
        "package",
        "range",
        "return",
        "select",
        "struct",
        "switch",
        "true",
        "type",
        "var",
    },
    "rust": {
        "as",
        "async",
        "await",
        "break",
        "const",
        "continue",
        "crate",
        "dyn",
        "else",
        "enum",
        "extern",
        "false",
        "fn",
        "for",
        "if",
        "impl",
        "in",
        "let",
        "loop",
        "match",
        "mod",
        "move",
        "mut",
        "pub",
        "ref",
        "return",
        "self",
        "Self",
        "static",
        "struct",
        "super",
        "trait",
        "true",
        "type",
        "unsafe",
        "use",
        "where",
        "while",
    },
    "ruby": {
        "alias",
        "and",
        "begin",
        "break",
        "case",
        "class",
        "def",
        "defined?",
        "do",
        "else",
        "elsif",
        "end",
        "ensure",
        "false",
        "for",
        "if",
        "in",
        "module",
        "next",
        "nil",
        "not",
        "or",
        "redo",
        "rescue",
        "retry",
        "return",
        "self",
        "super",
        "then",
        "true",
        "undef",
        "unless",
        "until",
        "when",
        "while",
        "yield",
    },
    "php": {
        "abstract",
        "and",
        "array",
        "as",
        "break",
        "callable",
        "case",
        "catch",
        "class",
        "clone",
        "const",
        "continue",
        "declare",
        "default",
        "do",
        "echo",
        "else",
        "elseif",
        "empty",
        "endfor",
        "endif",
        "endswitch",
        "endwhile",
        "extends",
        "false",
        "final",
        "finally",
        "foreach",
        "function",
        "global",
        "if",
        "implements",
        "include",
        "instanceof",
        "interface",
        "isset",
        "namespace",
        "new",
        "null",
        "or",
        "private",
        "protected",
        "public",
        "require",
        "return",
        "static",
        "switch",
        "throw",
        "trait",
        "true",
        "try",
        "use",
        "var",
        "while",
        "xor",
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
    "c": {"bool", "char", "double", "float", "int", "int32_t", "int64_t", "size_t", "uint32_t", "uint64_t", "void"},
    "cpp": {
        "bool",
        "char",
        "double",
        "float",
        "int",
        "int32_t",
        "int64_t",
        "size_t",
        "std",
        "string",
        "uint32_t",
        "uint64_t",
        "void",
    },
    "objc": {
        "NSArray",
        "BOOL",
        "CGFloat",
        "Class",
        "NSDictionary",
        "NSError",
        "NSInteger",
        "NSNumber",
        "NSObject",
        "NSString",
        "NSUInteger",
        "NSURL",
        "SEL",
        "UIView",
        "char",
        "double",
        "float",
        "id",
        "int",
        "void",
    },
    "js": {"Array", "BigInt", "Boolean", "Date", "Map", "Number", "Object", "Promise", "Set", "String", "Symbol"},
    "ts": {
        "Array",
        "BigInt",
        "Boolean",
        "Date",
        "Map",
        "Number",
        "Object",
        "Promise",
        "Record",
        "Set",
        "String",
        "Symbol",
    },
    "python": {"bool", "bytes", "dict", "float", "int", "list", "object", "set", "str", "tuple"},
    "swift": {"Any", "Array", "Bool", "Dictionary", "Double", "Float", "Int", "Optional", "Result", "Set", "String", "Void"},
    "go": {"bool", "byte", "error", "float32", "float64", "int", "int32", "int64", "rune", "string", "uint", "uint32", "uint64"},
    "rust": {"Box", "Option", "Result", "String", "Vec", "bool", "f32", "f64", "i32", "i64", "str", "u32", "u64", "usize"},
    "ruby": {"Array", "Class", "FalseClass", "Hash", "Integer", "Module", "NilClass", "Object", "String", "Symbol", "TrueClass"},
    "php": {"array", "bool", "callable", "float", "int", "iterable", "mixed", "object", "string", "void"},
}


def css_span(class_name: str, text: str) -> str:
    return f'<span class="{class_name}">{html.escape(text)}</span>'


def normalize_lang(lang: str) -> str:
    normalized = lang.lower().strip()
    normalized = LANG_ALIASES.get(normalized, normalized)
    if normalized not in SUPPORTED_LANGS:
        raise SystemExit(f"Unsupported language: {lang}. Supported: {', '.join(sorted(SUPPORTED_LANGS))}")
    return normalized


def language_registry() -> dict[str, object]:
    """输出语言注册表，让文档、校验脚本和测试只依赖这一份清单。"""

    return {
        "languages": sorted(SUPPORTED_LANGS),
        "aliases": {key: LANG_ALIASES[key] for key in sorted(LANG_ALIASES)},
    }


def infer_lang_from_diff_path(diff_path: str) -> str:
    """从 unified diff 的 ---/+++ 文件路径推断代码语言。"""

    path = diff_path.strip()
    if "\t" in path:
        path = path.split("\t", 1)[0]
    if len(path) >= 2 and path[0] == path[-1] == '"':
        path = path[1:-1]
    if path in {"/dev/null", "dev/null"}:
        return "text"
    if path.startswith(("a/", "b/")):
        path = path[2:]

    suffix = Path(path).suffix.lower().lstrip(".")
    if not suffix:
        return "text"

    lang = LANG_ALIASES.get(suffix, suffix)
    if lang in SUPPORTED_LANGS and lang != "diff":
        return lang
    return "text"


def read_source(path: str | None) -> str:
    if not path or path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def token_pattern(lang: str) -> re.Pattern[str]:
    """按语言返回一个保守 token 正则，避免过度解析。"""

    if lang == "python":
        comment = r"#[^\n]*"
        string = r"'''[\s\S]*?'''|\"\"\"[\s\S]*?\"\"\"|(?:r|R|f|F|fr|FR|rf|RF)?'(?:\\.|[^'\\])*'|(?:r|R|f|F|fr|FR|rf|RF)?\"(?:\\.|[^\"\\])*\""
    elif lang in {"bash", "ruby"}:
        comment = r"#[^\n]*"
        string = r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`'
    elif lang == "php":
        # PHP 同时支持 //、# 和 /* */ 注释；单独分支能避免把 shell 风格注释误扩散到其他 C-like 语言。
        comment = r"//[^\n]*|#[^\n]*|/\*[\s\S]*?\*/"
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
    number = r"\b(?:0[xX][0-9A-Fa-f_]+|\d[\d_]*(?:\.\d[\d_]*)?(?:[eE][+-]?\d[\d_]*)?[uUlLfFdD]*)\b"
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
    """高亮 C-like、脚本语言和常规语言片段。"""

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


# YAML/TOML/INI 都是报告里常见的配置片段；同时识别 : 和 = 可以覆盖三者的键名，
# 让校验脚本看到稳定的 tok-var，而不用为每种轻量配置格式维护一套解析器。
CONFIG_KEY_RE = re.compile(r"^(\s*)([A-Za-z0-9_.-]+)(\s*[:=])", re.MULTILINE)
MARKDOWN_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


def highlight_yaml(source: str) -> str:
    """高亮 YAML/配置片段里的 key、注释、字符串和数字。"""

    pieces: list[str] = []
    last = 0
    for match in CONFIG_KEY_RE.finditer(source):
        pieces.append(html.escape(source[last : match.start()]))
        pieces.append(html.escape(match.group(1)))
        pieces.append(css_span("tok-var", match.group(2)))
        pieces.append(html.escape(match.group(3)))
        last = match.end()

    tail = html.escape(source[last:])
    tail = re.sub(r"([#;].*)$", lambda m: css_span("tok-cmt", html.unescape(m.group(1))), tail, flags=re.MULTILINE)
    pieces.append(tail)
    return "".join(pieces)


def highlight_markdown(source: str) -> str:
    """高亮 Markdown 标题、引用、列表标记和行内代码。

    Markdown 常被放进报告说明或 README 片段里。这里刻意只标记结构性 token，
    避免为了完整 Markdown 解析引入依赖或误改正文转义边界。
    """

    pieces: list[str] = []
    for line in source.splitlines(keepends=True):
        newline = "\n" if line.endswith("\n") else ""
        body = line[:-1] if newline else line
        heading = re.match(r"^(\s{0,3})(#{1,6})(\s+.*)?$", body)
        quote = re.match(r"^(\s{0,3})(>+)(\s+.*)?$", body)
        bullet = re.match(r"^(\s*)([-+*]|\d+\.)(\s+.*)$", body)

        if heading:
            pieces.append(html.escape(heading.group(1)))
            pieces.append(css_span("tok-key", heading.group(2)))
            pieces.append(highlight_markdown_inline(heading.group(3) or ""))
        elif quote:
            pieces.append(html.escape(quote.group(1)))
            pieces.append(css_span("tok-cmt", quote.group(2)))
            pieces.append(highlight_markdown_inline(quote.group(3) or ""))
        elif bullet:
            pieces.append(html.escape(bullet.group(1)))
            pieces.append(css_span("tok-key", bullet.group(2)))
            pieces.append(highlight_markdown_inline(bullet.group(3)))
        else:
            pieces.append(highlight_markdown_inline(body))
        pieces.append(newline)
    return "".join(pieces)


def highlight_markdown_inline(text: str) -> str:
    """只处理 Markdown 行内代码，其余内容保持普通 HTML 转义。"""

    pieces: list[str] = []
    last = 0
    for match in MARKDOWN_INLINE_CODE_RE.finditer(text):
        pieces.append(html.escape(text[last : match.start()]))
        pieces.append(css_span("tok-str", match.group(0)))
        last = match.end()
    pieces.append(html.escape(text[last:]))
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


def highlight_diff_code(code: str, lang: str) -> str:
    """对 diff 代码列做语法高亮；未知语言保持安全转义文本。"""

    if lang in {"text", "diff"}:
        return html.escape(code)
    return highlight(code, lang)


def render_diff_row(row_class: str, marker: str, old_num: int | None, new_num: int | None, code: str, lang: str) -> str:
    """生成一行带 old/new 行号的 diff viewer 表格。"""

    old_text = str(old_num) if old_num is not None else ""
    new_text = str(new_num) if new_num is not None else ""
    highlighted_code = highlight_diff_code(code, lang)
    return (
        f'    <tr class="diff-line {row_class}">'
        f'<td class="diff-gutter">{html.escape(marker)}</td>'
        f'<td class="diff-num diff-old-num">{old_text}</td>'
        f'<td class="diff-num diff-new-num">{new_text}</td>'
        f'<td class="diff-code language-{html.escape(lang)}">{highlighted_code}</td>'
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
    current_lang = "text"

    for line in source.splitlines():
        hunk = HUNK_RE.match(line)
        if hunk:
            old_line = int(hunk.group(1))
            new_line = int(hunk.group(2))
            rows.append(render_diff_note("diff-hunk", line))
            continue

        if line.startswith("--- "):
            old_lang = infer_lang_from_diff_path(line[4:])
            if old_lang != "text":
                current_lang = old_lang
            rows.append(render_diff_note("diff-meta", line))
            continue

        if line.startswith("+++ "):
            new_lang = infer_lang_from_diff_path(line[4:])
            if new_lang != "text" or current_lang == "text":
                current_lang = new_lang
            rows.append(render_diff_note("diff-meta", line))
            continue

        if line.startswith(("diff ", "index ")):
            rows.append(render_diff_note("diff-meta", line))
            continue

        if line.startswith("\\"):
            rows.append(render_diff_note("diff-meta", line))
            continue

        if line.startswith("-") and old_line is not None:
            rows.append(render_diff_row("diff-del", "-", old_line, None, line[1:], current_lang))
            old_line += 1
            continue

        if line.startswith("+") and new_line is not None:
            rows.append(render_diff_row("diff-add", "+", None, new_line, line[1:], current_lang))
            new_line += 1
            continue

        if line.startswith(" ") and old_line is not None and new_line is not None:
            rows.append(render_diff_row("diff-context", "", old_line, new_line, line[1:], current_lang))
            old_line += 1
            new_line += 1
            continue

        rows.append(render_diff_note("diff-meta", line))

    if not rows:
        rows.append(render_diff_note("diff-meta", ""))

    return (
        '<section class="diff-card diff-viewer">\n'
        '  <div class="diff-header">\n'
        '    <span class="change-chip change-mod">代码差异</span>\n'
        '    <span class="muted">统一 diff · old/new 行号</span>\n'
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
    if lang in {"yaml", "toml", "ini"}:
        return highlight_yaml(source)
    if lang == "markdown":
        return highlight_markdown(source)
    if lang == "bash":
        return highlight_bash(source)
    return highlight_general(source, lang)


def can_use_pygments() -> bool:
    """检查当前环境是否可用 Pygments，不触发安装或联网。"""

    return importlib.util.find_spec("pygments") is not None or shutil.which("pygmentize") is not None


def pygments_lexer_name(lang: str) -> str:
    return {
        "cpp": "cpp",
        "js": "javascript",
        "markdown": "markdown",
        "objc": "objective-c",
        "ts": "typescript",
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
    parser.add_argument("--lang", help=f"语言：{', '.join(sorted(SUPPORTED_LANGS))}；常见文件后缀和别名会自动映射。")
    parser.add_argument("--list-langs", action="store_true", help="输出当前支持语言和别名的 JSON 注册表。")
    parser.add_argument("--mode", choices=["code", "diff-viewer"], default="code", help="输出模式；diff-viewer 用于带 old/new 行号的差异视图。")
    parser.add_argument("--diff-view", action="store_true", help="等同于 --mode diff-viewer，仅支持 --lang diff。")
    parser.add_argument("--engine", choices=["builtin", "auto", "pygments"], default="builtin", help="高亮引擎：builtin 为零依赖默认值；auto/pygments 可使用本机 Pygments 预渲染。")
    parser.add_argument("--no-copy", action="store_true", help="不生成复制按钮。")
    args = parser.parse_args()
    if not args.list_langs and not args.lang:
        parser.error("--lang is required unless --list-langs is used")
    return args


def main() -> None:
    args = parse_args()
    if args.list_langs:
        json.dump(language_registry(), sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return

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
