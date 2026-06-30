#!/usr/bin/env python3
"""检查 SVG 渲染 PNG 的明显视觉问题。

该脚本用 Python 标准库解析 8-bit PNG，计算非背景像素包围盒：
- 渲染结果是否几乎空白。
- 内容是否贴边或被裁切。
- 四周留白是否明显过大。

它只做像素级低成本 QA，不能替代人工或模型读取 PNG 后的版面自审。
"""

from __future__ import annotations

import argparse
import struct
import sys
import zlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
BACKGROUND_THRESHOLD = 12
ALPHA_THRESHOLD = 12
MAX_MARGIN_PX = 96
MAX_MARGIN_RATIO = 0.12
MIN_EDGE_MARGIN_PX = 6
MIN_CONTENT_AREA_RATIO = 0.01


@dataclass
class PngImage:
    width: int
    height: int
    color_type: int
    rows: list[bytes]

    @property
    def channels(self) -> int:
        return {0: 1, 2: 3, 4: 2, 6: 4}[self.color_type]


@dataclass
class BBox:
    min_x: int
    min_y: int
    max_x: int
    max_y: int

    @property
    def width(self) -> int:
        return self.max_x - self.min_x + 1

    @property
    def height(self) -> int:
        return self.max_y - self.min_y + 1


def read_png(path: Path) -> PngImage:
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("不是 PNG 文件")

    offset = len(PNG_SIGNATURE)
    width = height = bit_depth = color_type = interlace = None
    idat_parts: list[bytes] = []

    while offset + 8 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        chunk_data = data[offset + 8 : offset + 8 + length]
        offset += 12 + length

        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, _, _, interlace = struct.unpack(">IIBBBBB", chunk_data)
        elif chunk_type == b"IDAT":
            idat_parts.append(chunk_data)
        elif chunk_type == b"IEND":
            break

    if width is None or height is None or bit_depth is None or color_type is None or interlace is None:
        raise ValueError("缺少 IHDR")
    if bit_depth != 8:
        raise ValueError(f"暂只支持 8-bit PNG，当前 bit depth={bit_depth}")
    if color_type not in {0, 2, 4, 6}:
        raise ValueError(f"暂只支持 grayscale/RGB/RGBA PNG，当前 color type={color_type}")
    if interlace != 0:
        raise ValueError("暂不支持 interlaced PNG")

    channels = {0: 1, 2: 3, 4: 2, 6: 4}[color_type]
    raw = zlib.decompress(b"".join(idat_parts))
    stride = width * channels
    rows: list[bytes] = []
    prev = bytes(stride)
    cursor = 0
    for _ in range(height):
        filter_type = raw[cursor]
        cursor += 1
        scanline = bytearray(raw[cursor : cursor + stride])
        cursor += stride
        recon = unfilter(scanline, prev, filter_type, channels)
        rows.append(bytes(recon))
        prev = bytes(recon)

    return PngImage(width=width, height=height, color_type=color_type, rows=rows)


def unfilter(scanline: bytearray, prev: bytes, filter_type: int, bpp: int) -> bytearray:
    if filter_type == 0:
        return scanline
    for i, value in enumerate(scanline):
        left = scanline[i - bpp] if i >= bpp else 0
        up = prev[i] if prev else 0
        up_left = prev[i - bpp] if prev and i >= bpp else 0
        if filter_type == 1:
            scanline[i] = (value + left) & 0xFF
        elif filter_type == 2:
            scanline[i] = (value + up) & 0xFF
        elif filter_type == 3:
            scanline[i] = (value + ((left + up) // 2)) & 0xFF
        elif filter_type == 4:
            scanline[i] = (value + paeth(left, up, up_left)) & 0xFF
        else:
            raise ValueError(f"未知 PNG filter type={filter_type}")
    return scanline


def paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def pixel_at(image: PngImage, x: int, y: int) -> tuple[int, int, int, int]:
    channels = image.channels
    start = x * channels
    raw = image.rows[y][start : start + channels]
    if image.color_type == 0:
        value = raw[0]
        return value, value, value, 255
    if image.color_type == 2:
        return raw[0], raw[1], raw[2], 255
    if image.color_type == 4:
        value = raw[0]
        return value, value, value, raw[1]
    return raw[0], raw[1], raw[2], raw[3]


def estimate_background(image: PngImage) -> tuple[int, int, int, int]:
    samples = [
        pixel_at(image, 0, 0),
        pixel_at(image, image.width - 1, 0),
        pixel_at(image, 0, image.height - 1),
        pixel_at(image, image.width - 1, image.height - 1),
    ]
    return Counter(samples).most_common(1)[0][0]


def is_content(pixel: tuple[int, int, int, int], background: tuple[int, int, int, int]) -> bool:
    if pixel[3] <= ALPHA_THRESHOLD and background[3] <= ALPHA_THRESHOLD:
        return False
    return max(abs(pixel[index] - background[index]) for index in range(4)) > BACKGROUND_THRESHOLD


def content_bbox(image: PngImage) -> BBox | None:
    background = estimate_background(image)
    min_x = image.width
    min_y = image.height
    max_x = -1
    max_y = -1
    for y in range(image.height):
        for x in range(image.width):
            if is_content(pixel_at(image, x, y), background):
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
    if max_x < 0:
        return None
    return BBox(min_x=min_x, min_y=min_y, max_x=max_x, max_y=max_y)


def check_image(image: PngImage) -> list[str]:
    errors: list[str] = []
    bbox = content_bbox(image)
    if bbox is None:
        return ["PNG 几乎为空白：未检测到区别于背景的内容像素。"]

    content_area_ratio = (bbox.width * bbox.height) / (image.width * image.height)
    if content_area_ratio < MIN_CONTENT_AREA_RATIO:
        errors.append(
            f"内容包围盒只占画布 {content_area_ratio:.1%}，图可能缩在一角或主体过小。"
        )

    margins = {
        "左": bbox.min_x,
        "右": image.width - 1 - bbox.max_x,
        "上": bbox.min_y,
        "下": image.height - 1 - bbox.max_y,
    }
    limits = {
        "左": max(MAX_MARGIN_PX, int(image.width * MAX_MARGIN_RATIO)),
        "右": max(MAX_MARGIN_PX, int(image.width * MAX_MARGIN_RATIO)),
        "上": max(MAX_MARGIN_PX, int(image.height * MAX_MARGIN_RATIO)),
        "下": max(MAX_MARGIN_PX, int(image.height * MAX_MARGIN_RATIO)),
    }
    for side, margin in margins.items():
        if margin > limits[side]:
            errors.append(f"{side}侧留白 {margin}px 过大，超过阈值 {limits[side]}px；请按内容包围盒裁短 viewBox。")
        if margin < MIN_EDGE_MARGIN_PX:
            errors.append(f"{side}侧内容距离画布边缘仅 {margin}px，可能被裁切或贴边。")

    if margins["下"] - margins["上"] > 80 and margins["下"] > margins["上"] * 2:
        errors.append(
            f"上下留白不平衡：上 {margins['上']}px、下 {margins['下']}px；请裁短底部或下移主体。"
        )
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="检查 SVG 渲染 PNG 的空白、裁切和留白。")
    parser.add_argument("png", type=Path, help="由 SVG 渲染出的 PNG 文件")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.png.is_file():
        print(f"输入 PNG 不存在：{args.png}", file=sys.stderr)
        return 1
    try:
        image = read_png(args.png)
        errors = check_image(image)
    except ValueError as exc:
        print(f"FAIL {args.png}")
        print(f"- {exc}")
        return 1

    if errors:
        print(f"FAIL {args.png}")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"PASS {args.png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
