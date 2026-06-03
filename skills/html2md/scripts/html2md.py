#!/usr/bin/env python3
"""Convert local HTML files to GitHub-Flavored Markdown.

The converter intentionally uses only the Python standard library so the
html2md skill works in fresh Codex/Claude environments without dependency
installation.
"""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse


BLOCK_TAGS = {
    "address",
    "article",
    "aside",
    "blockquote",
    "body",
    "details",
    "div",
    "dl",
    "fieldset",
    "figcaption",
    "figure",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "html",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "summary",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "ul",
}


class Node:
    def __init__(self, tag: str | None = None, attrs=None, text: str | None = None):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.text = text
        self.children: list[Node] = []

    def attr(self, name: str, default: str = "") -> str:
        return self.attrs.get(name, default)

    def classes(self) -> set[str]:
        return set(self.attr("class", "").split())


class TreeParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("document")
        self.stack = [self.root]
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs):
        tag = tag.lower()
        if tag in {"style", "script"}:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag == "br":
            self.stack[-1].children.append(Node(text="\n"))
            return
        if tag in {"meta", "link", "img", "input"}:
            return
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        self.stack.append(node)

    def handle_endtag(self, tag: str):
        tag = tag.lower()
        if tag in {"style", "script"}:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.skip_depth:
            return
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                self.stack = self.stack[:index]
                return

    def handle_data(self, data: str):
        if not self.skip_depth:
            self.stack[-1].children.append(Node(text=data))


def parse_path(value: str) -> Path:
    parsed = urlparse(value)
    if parsed.scheme == "file":
        return Path(unquote(parsed.path))
    return Path(value).expanduser()


def find_first(node: Node, tag: str) -> Node | None:
    if node.tag == tag:
        return node
    for child in node.children:
        found = find_first(child, tag)
        if found:
            return found
    return None


def raw_text(node: Node) -> str:
    if node.text is not None:
        return node.text
    if node.tag == "button":
        return ""
    return "".join(raw_text(child) for child in node.children)


def collapse_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    parts = [re.sub(r"[ \t\r\f\v]+", " ", part).strip() for part in text.split("\n")]
    return "\n".join(part for part in parts if part)


def is_block(node: Node) -> bool:
    return node.text is None and node.tag in BLOCK_TAGS


def code_ticks(text: str) -> str:
    text = text.strip()
    if not text:
        return " `` "
    longest = max((len(match.group(0)) for match in re.finditer(r"`+", text)), default=0)
    ticks = "`" * (longest + 1)
    if text.startswith("`") or text.endswith("`"):
        return f" {ticks} {text} {ticks} "
    return f" {ticks}{text}{ticks} "


def cleanup_inline(text: str) -> str:
    text = text.replace(" \n", "\n").replace("\n ", "\n")
    text = re.sub(r"\s*→\s*", " → ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\s+([，。；：？！、）\)\]】])", r"\1", text)
    text = re.sub(r"([（\(【\[])\s+", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def render_inline(node: Node) -> str:
    if node.text is not None:
        return collapse_text(node.text)
    if node.tag == "button":
        return ""

    inner = "".join(render_inline(child) for child in node.children)
    inner = re.sub(r" {2,}", " ", inner)
    if node.tag == "code":
        return code_ticks(raw_text(node))
    if node.tag in {"b", "strong"}:
        return f"**{inner.strip()}**" if inner.strip() else ""
    if node.tag in {"i", "em"}:
        return f"*{inner.strip()}*" if inner.strip() else ""
    if node.tag == "del":
        return f"~~{inner.strip()}~~" if inner.strip() else ""
    if node.tag == "ins":
        return inner
    if node.tag == "a":
        href = node.attr("href")
        label = inner.strip() or href
        return f"[{label}]({href})" if href else label
    return inner


def paragraph_from_inline(text: str) -> str:
    text = cleanup_inline(text)
    return f"{text}\n\n" if text else ""


def fence_language(node: Node) -> str:
    for child in node.children:
        if child.tag == "code":
            match = re.search(r"language-([A-Za-z0-9_+-]+)", child.attr("class"))
            if match:
                return match.group(1)
    return ""


def render_pre(node: Node) -> str:
    language = fence_language(node)
    text = raw_text(node).strip("\n").rstrip()
    return f"```{language}\n{text}\n```\n\n"


def collect_rows(table: Node) -> list[Node]:
    rows: list[Node] = []

    def walk(node: Node) -> None:
        if node.tag == "tr":
            rows.append(node)
            return
        for child in node.children:
            walk(child)

    walk(table)
    return rows


def direct_cells(row: Node) -> list[Node]:
    return [child for child in row.children if child.tag in {"td", "th"}]


def escape_table_cell(text: str) -> str:
    text = cleanup_inline(text)
    text = text.replace("\n", "<br>")
    return text.replace("|", r"\|")


def render_diff_table(table: Node) -> str:
    lines: list[str] = []
    for row in collect_rows(table):
        cells = direct_cells(row)
        if len(cells) < 3:
            continue
        sign = raw_text(cells[0]).strip()
        sign = sign if sign in {"+", "-"} else " "
        number = raw_text(cells[1]).strip()
        code = raw_text(cells[2]).rstrip()
        if not number and not code.strip():
            continue
        lines.append(f"{sign}{number.rjust(4)} {code}")
    return "```diff\n" + "\n".join(lines) + "\n```\n\n" if lines else ""


def render_table(table: Node) -> str:
    if "diff-table" in table.classes():
        return render_diff_table(table)

    rows = []
    header_from_th = False
    for row in collect_rows(table):
        cells = direct_cells(row)
        if not cells:
            continue
        header_from_th = header_from_th or any(cell.tag == "th" for cell in cells)
        rows.append([escape_table_cell(render_inline(cell)) for cell in cells])
    if not rows:
        return ""

    width = max(len(row) for row in rows)
    padded = [row + [""] * (width - len(row)) for row in rows]
    first_row = direct_cells(collect_rows(table)[0])
    if header_from_th and any(cell.tag == "th" for cell in first_row):
        header, body = padded[0], padded[1:]
    else:
        header = ["字段", "说明"] if width == 2 else [f"列{index + 1}" for index in range(width)]
        body = padded

    output = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * width) + " |",
    ]
    output.extend("| " + " | ".join(row) + " |" for row in body)
    return "\n".join(output) + "\n\n"


def render_list(node: Node, ordered: bool = False, indent: int = 0) -> str:
    output: list[str] = []
    index = 1
    for child in node.children:
        if child.tag != "li":
            continue
        marker = f"{index}. " if ordered else "- "
        rendered = render_li(child, indent + len(marker))
        if rendered:
            lines = rendered.rstrip().splitlines()
            output.append(" " * indent + marker + lines[0])
            output.extend(" " * (indent + len(marker)) + line for line in lines[1:])
        index += 1
    return "\n".join(output) + "\n\n" if output else ""


def render_li(node: Node, indent: int) -> str:
    inline_parts: list[str] = []
    block_parts: list[str] = []
    for child in node.children:
        if child.tag in {"ul", "ol", "table", "pre"}:
            if inline_parts:
                block_parts.append(cleanup_inline("".join(inline_parts)))
                inline_parts = []
            block_parts.append(render_block(child, indent).rstrip())
        elif is_block(child):
            inline_parts.append(render_inline(child))
        else:
            inline_parts.append(render_inline(child))
    if inline_parts:
        block_parts.insert(0, cleanup_inline("".join(inline_parts)))
    return "\n".join(part for part in block_parts if part)


def render_details(node: Node) -> str:
    summary = ""
    body_parts: list[str] = []
    for child in node.children:
        if child.tag == "summary":
            summary = cleanup_inline(render_inline(child))
        else:
            body_parts.append(render_block(child))
    if not summary:
        return "".join(body_parts)
    return f"#### {summary}\n\n" + "".join(body_parts)


def render_generic_container(node: Node) -> str:
    output: list[str] = []
    inline_parts: list[str] = []
    for child in node.children:
        if child.tag == "button":
            continue
        if is_block(child):
            if inline_parts:
                output.append(paragraph_from_inline("".join(inline_parts)))
                inline_parts = []
            output.append(render_block(child))
        else:
            inline_parts.append(render_inline(child))
    if inline_parts:
        output.append(paragraph_from_inline("".join(inline_parts)))
    return "".join(output)


def render_doc_meta(node: Node) -> str:
    chips = [cleanup_inline(render_inline(child)) for child in node.children]
    chips = [chip for chip in chips if chip]
    return "> " + " · ".join(chips) + "\n\n" if chips else ""


def render_grid(node: Node) -> str:
    items: list[str] = []
    for child in node.children:
        if child.tag != "div":
            continue
        tag_text = ""
        title = ""
        desc = ""
        for grand in child.children:
            if grand.tag == "span" and "tag" in grand.classes():
                tag_text = cleanup_inline(render_inline(grand))
            elif grand.tag == "b":
                title = cleanup_inline(render_inline(grand)).strip("*")
            elif grand.tag == "span":
                desc = cleanup_inline(render_inline(grand))
        item = f"**{tag_text}：{title}**" if tag_text and title else f"**{title}**" if title else ""
        if desc:
            item = f"{item}：{desc}" if item else desc
        if item:
            items.append(item)
    return "".join(f"- {item}\n" for item in items) + "\n" if items else ""


def render_block(node: Node, indent: int = 0) -> str:
    if node.text is not None:
        return paragraph_from_inline(node.text)
    tag = node.tag
    if tag in {"document", "html", "body", "main", "article", "section", "header", "footer"}:
        return "".join(render_block(child, indent) for child in node.children)
    if tag and re.fullmatch(r"h[1-6]", tag):
        text = cleanup_inline(render_inline(node))
        level = int(tag[1])
        return f"{'#' * level} {text}\n\n" if text else ""
    if tag == "p":
        return paragraph_from_inline(render_inline(node))
    if tag == "pre":
        return render_pre(node)
    if tag == "table":
        return render_table(node)
    if tag == "ul":
        return render_list(node, ordered=False, indent=indent)
    if tag == "ol":
        return render_list(node, ordered=True, indent=indent)
    if tag == "blockquote":
        body = render_generic_container(node).strip()
        return "\n".join("> " + line if line else ">" for line in body.splitlines()) + "\n\n" if body else ""
    if tag == "details":
        return render_details(node)
    if tag == "hr":
        return "---\n\n"
    if tag == "div" and "doc-meta" in node.classes():
        return render_doc_meta(node)
    if tag == "div" and "grid" in node.classes():
        return render_grid(node)
    return render_generic_container(node)


def tidy_markdown(text: str) -> str:
    text = re.sub(r"\n[ \t]*\n```\n", "\n```\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip() + "\n"


def convert_html(html: str) -> str:
    parser = TreeParser()
    parser.feed(html)
    main_node = find_first(parser.root, "main") or find_first(parser.root, "body") or parser.root
    return tidy_markdown(render_block(main_node))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert local HTML to Markdown.")
    parser.add_argument("input", help="Input HTML path or file:// URL")
    parser.add_argument("output", nargs="?", help="Output Markdown path; defaults to input basename with .md")
    args = parser.parse_args(argv)

    input_path = parse_path(args.input)
    if not input_path.is_file():
        parser.error(f"input file does not exist: {input_path}")
    output_path = parse_path(args.output) if args.output else input_path.with_suffix(".md")

    markdown = convert_html(input_path.read_text(encoding="utf-8"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
