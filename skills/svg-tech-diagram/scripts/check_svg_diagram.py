#!/usr/bin/env python3
"""对手写 SVG 技术图做轻量几何闸门检查。

脚本只覆盖确定性强的版面问题：
- 背景 rect 没覆盖 viewBox。
- 多条箭头终点挤在同一小区域。
- 路径采样点穿过节点矩形内部。

它不能替代渲染 PNG 后的人工视觉自审；复杂遮挡、文本压线和整体美观仍要看图确认。
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree


NUMBER_RE = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")
TOKEN_RE = re.compile(r"[MmLlHhVvCcQqZz]|[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")
TRANSLATE_RE = re.compile(r"translate\(\s*([-.0-9eE]+)(?:[\s,]+([-.0-9eE]+))?\s*\)")
GEOMETRY_TAGS = {"rect", "path", "g", "svg"}
SKIP_TAGS = {"defs", "marker", "style", "title", "desc", "clipPath", "mask", "pattern", "linearGradient", "radialGradient"}

END_CLUSTER_X = 44.0
END_CLUSTER_Y = 44.0
RECT_INSET = 4.0
BACKGROUND_TOLERANCE = 1.5


@dataclass
class ViewBox:
    x: float
    y: float
    width: float
    height: float


@dataclass
class Rect:
    x: float
    y: float
    width: float
    height: float
    label: str
    classes: set[str]
    is_background: bool = False

    def contains_inner(self, point: tuple[float, float], inset: float = RECT_INSET) -> bool:
        px, py = point
        return (
            self.x + inset < px < self.x + self.width - inset
            and self.y + inset < py < self.y + self.height - inset
        )


@dataclass
class PathShape:
    points: list[tuple[float, float]]
    label: str

    @property
    def end(self) -> tuple[float, float] | None:
        return self.points[-1] if self.points else None


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_float(value: str | None, default: float = 0.0) -> float:
    if not value:
        return default
    match = NUMBER_RE.search(value)
    return float(match.group(0)) if match else default


def parse_viewbox(root: ElementTree.Element) -> ViewBox | None:
    raw = root.attrib.get("viewBox")
    if raw:
        numbers = [float(part) for part in NUMBER_RE.findall(raw)]
        if len(numbers) == 4:
            return ViewBox(*numbers)

    width = parse_float(root.attrib.get("width"))
    height = parse_float(root.attrib.get("height"))
    if width > 0 and height > 0:
        return ViewBox(0.0, 0.0, width, height)
    return None


def parse_translate(value: str | None) -> tuple[float, float]:
    if not value:
        return 0.0, 0.0
    dx = dy = 0.0
    for match in TRANSLATE_RE.finditer(value):
        dx += float(match.group(1))
        dy += float(match.group(2) or 0)
    return dx, dy


def element_label(element: ElementTree.Element, fallback: str) -> str:
    bits = [fallback]
    if element.attrib.get("id"):
        bits.append("#" + element.attrib["id"])
    if element.attrib.get("class"):
        bits.append("." + ".".join(element.attrib["class"].split()))
    return "".join(bits)


def is_connector_path(element: ElementTree.Element) -> bool:
    classes = set(element.attrib.get("class", "").split())
    if classes & {"arrow", "connector", "flow-line", "link-line"}:
        return True
    if element.attrib.get("marker-end") or element.attrib.get("marker-start"):
        return True
    return False


def collect_shapes(
    element: ElementTree.Element,
    offset: tuple[float, float] = (0.0, 0.0),
) -> tuple[list[Rect], list[PathShape]]:
    tag = local_name(element.tag)
    if tag in SKIP_TAGS:
        return [], []

    own_dx, own_dy = parse_translate(element.attrib.get("transform"))
    dx = offset[0] + own_dx
    dy = offset[1] + own_dy
    rects: list[Rect] = []
    paths: list[PathShape] = []

    if tag == "rect":
        rects.append(
            Rect(
                x=parse_float(element.attrib.get("x")) + dx,
                y=parse_float(element.attrib.get("y")) + dy,
                width=parse_float(element.attrib.get("width")),
                height=parse_float(element.attrib.get("height")),
                label=element_label(element, "rect"),
                classes=set(element.attrib.get("class", "").split()),
            )
        )
    elif tag == "path":
        points = parse_path_points(element.attrib.get("d", "")) if is_connector_path(element) else []
        if points:
            paths.append(
                PathShape(
                    points=[(x + dx, y + dy) for x, y in points],
                    label=element_label(element, "path"),
                )
            )

    for child in element:
        child_rects, child_paths = collect_shapes(child, (dx, dy))
        rects.extend(child_rects)
        paths.extend(child_paths)
    return rects, paths


def parse_path_points(d: str) -> list[tuple[float, float]]:
    tokens = TOKEN_RE.findall(d or "")
    if not tokens:
        return []

    index = 0
    command = ""
    current = (0.0, 0.0)
    start = (0.0, 0.0)
    points: list[tuple[float, float]] = []

    def is_command(token: str) -> bool:
        return len(token) == 1 and token.isalpha()

    def take_number() -> float | None:
        nonlocal index
        if index >= len(tokens) or is_command(tokens[index]):
            return None
        value = float(tokens[index])
        index += 1
        return value

    def absolute_pair(x: float, y: float, relative: bool) -> tuple[float, float]:
        return (current[0] + x, current[1] + y) if relative else (x, y)

    while index < len(tokens):
        if is_command(tokens[index]):
            command = tokens[index]
            index += 1
        if not command:
            break

        relative = command.islower()
        cmd = command.upper()

        if cmd == "M":
            x = take_number()
            y = take_number()
            if x is None or y is None:
                break
            current = absolute_pair(x, y, relative)
            start = current
            points.append(current)
            command = "l" if relative else "L"
        elif cmd == "L":
            x = take_number()
            y = take_number()
            if x is None or y is None:
                break
            current = absolute_pair(x, y, relative)
            points.append(current)
        elif cmd == "H":
            x = take_number()
            if x is None:
                break
            current = (current[0] + x, current[1]) if relative else (x, current[1])
            points.append(current)
        elif cmd == "V":
            y = take_number()
            if y is None:
                break
            current = (current[0], current[1] + y) if relative else (current[0], y)
            points.append(current)
        elif cmd == "C":
            values = [take_number() for _ in range(6)]
            if any(value is None for value in values):
                break
            x1, y1, x2, y2, x, y = [float(value) for value in values if value is not None]
            p0 = current
            p1 = absolute_pair(x1, y1, relative)
            p2 = absolute_pair(x2, y2, relative)
            p3 = absolute_pair(x, y, relative)
            points.extend(sample_cubic(p0, p1, p2, p3))
            current = p3
        elif cmd == "Q":
            values = [take_number() for _ in range(4)]
            if any(value is None for value in values):
                break
            x1, y1, x, y = [float(value) for value in values if value is not None]
            p0 = current
            p1 = absolute_pair(x1, y1, relative)
            p2 = absolute_pair(x, y, relative)
            points.extend(sample_quadratic(p0, p1, p2))
            current = p2
        elif cmd == "Z":
            current = start
            points.append(current)
            command = ""
        else:
            break

    return dedupe_points(points)


def sample_cubic(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    steps: int = 14,
) -> list[tuple[float, float]]:
    return [
        (
            (1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t**2 * p2[0] + t**3 * p3[0],
            (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t**2 * p2[1] + t**3 * p3[1],
        )
        for t in (i / steps for i in range(1, steps + 1))
    ]


def sample_quadratic(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    steps: int = 10,
) -> list[tuple[float, float]]:
    return [
        (
            (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t**2 * p2[0],
            (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t**2 * p2[1],
        )
        for t in (i / steps for i in range(1, steps + 1))
    ]


def dedupe_points(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    for point in points:
        if not result or distance(point, result[-1]) > 0.1:
            result.append(point)
    return result


def distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def mark_background_rects(rects: list[Rect], viewbox: ViewBox) -> None:
    for rect in rects:
        rect.is_background = (
            abs(rect.x - viewbox.x) <= BACKGROUND_TOLERANCE
            and abs(rect.y - viewbox.y) <= BACKGROUND_TOLERANCE
            and abs(rect.width - viewbox.width) <= BACKGROUND_TOLERANCE
            and abs(rect.height - viewbox.height) <= BACKGROUND_TOLERANCE
        )


def check_background(rects: list[Rect], viewbox: ViewBox) -> list[str]:
    if any(rect.is_background for rect in rects):
        return []
    return [
        "背景 <rect> 未覆盖 viewBox；自适应画布后需要同步 rect x/y/width/height，避免导出或嵌入时露底。"
    ]


def check_endpoint_clusters(paths: list[PathShape]) -> list[str]:
    errors: list[str] = []
    ends = [(path, path.end) for path in paths if path.end]
    reported: set[tuple[str, ...]] = set()
    for path, point in ends:
        assert point is not None
        cluster = [
            other
            for other, other_point in ends
            if other_point
            and abs(other_point[0] - point[0]) <= END_CLUSTER_X
            and abs(other_point[1] - point[1]) <= END_CLUSTER_Y
        ]
        if len(cluster) < 3:
            continue
        key = tuple(sorted(item.label for item in cluster))
        if key in reported:
            continue
        reported.add(key)
        avg_x = sum(item.end[0] for item in cluster if item.end) / len(cluster)
        avg_y = sum(item.end[1] for item in cluster if item.end) / len(cluster)
        errors.append(
            f"{len(cluster)} 条路径终点聚集在 ({avg_x:.0f}, {avg_y:.0f}) 附近；多来源汇聚应先进入变量池/汇聚层，再用单箭头指向目标。"
        )
    return errors


def check_paths_cross_rects(paths: list[PathShape], rects: list[Rect]) -> list[str]:
    errors: list[str] = []
    background_classes = {"group", "lane", "swimlane", "background", "panel-bg", "section-bg"}
    obstacles = [
        rect
        for rect in rects
        if not rect.is_background
        and not (rect.classes & background_classes)
        and rect.width > 16
        and rect.height > 16
    ]
    for path in paths:
        if len(path.points) < 4:
            continue
        interior_points = path.points[2:-2]
        for rect in obstacles:
            hits = [point for point in interior_points if rect.contains_inner(point)]
            if len(hits) >= 2:
                errors.append(
                    f"{path.label} 的连线采样点进入 {rect.label} 内部；箭头需要走节点外侧 gutter，端点停在边缘。"
                )
                break
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="检查 SVG 技术图的明显几何版面问题。")
    parser.add_argument("svg", type=Path, help="待检查的 .svg 文件")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.svg.is_file():
        print(f"输入 SVG 不存在：{args.svg}", file=sys.stderr)
        return 1

    try:
        root = ElementTree.parse(args.svg).getroot()
    except ElementTree.ParseError as exc:
        print(f"FAIL {args.svg}", file=sys.stderr)
        print(f"- SVG XML 解析失败：{exc}", file=sys.stderr)
        return 1

    viewbox = parse_viewbox(root)
    if not viewbox:
        print(f"FAIL {args.svg}")
        print("- 缺少 viewBox，无法做自适应画布和几何检查。")
        return 1

    rects, paths = collect_shapes(root)
    mark_background_rects(rects, viewbox)
    errors: list[str] = []
    errors.extend(check_background(rects, viewbox))
    errors.extend(check_endpoint_clusters(paths))
    errors.extend(check_paths_cross_rects(paths, rects))

    if errors:
        print(f"FAIL {args.svg}")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"PASS {args.svg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
