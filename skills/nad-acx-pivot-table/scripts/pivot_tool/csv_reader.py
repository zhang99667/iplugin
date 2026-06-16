"""CSV/XLSX 读取 + 字段分析，产出 FieldMaps 数据结构。"""

from __future__ import annotations

import csv
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

from pivot_tool.config import PivotConfig, ColumnDef
from pivot_tool.xml_utils import clean


@dataclass
class FieldMaps:
    """CSV 数据经字段分析后的结构化结果。"""

    headers: list[str]
    rows: list[list[str]]

    # 枚举字段的去重有序值列表 {col_index: [val, ...]}
    enumerated_items: dict[int, list] = field(default_factory=dict)

    # 值→索引映射 {col_index: {val: idx}}
    item_index_maps: dict[int, dict] = field(default_factory=dict)

    # 数值字段的 (min, max) {col_index: (min_val, max_val)}
    stats: dict[int, tuple] = field(default_factory=dict)

    # 各字段是否有空值 {col_index: bool}
    has_blanks: dict[int, bool] = field(default_factory=dict)

    @property
    def num_rows(self) -> int:
        return len(self.rows)

    @property
    def num_cols(self) -> int:
        return len(self.headers)


_TEXT_ENCODINGS = ("utf-8-sig", "utf-8", "gbk", "gb18030")
_TEXT_DELIMITERS = ",\t;|"


def _read_text(path: str) -> str:
    """按常见导出编码读取文本文件。"""
    for enc in _TEXT_ENCODINGS:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(
        "text", b"", 0, 1,
        f"无法解码 {path}（已尝试 {'/'.join(_TEXT_ENCODINGS)}）",
    )


def _sniff_delimiter(path: str, lines: list[str]) -> str:
    """从样本文本中识别分隔符，只接受常见表格分隔符。"""
    sample = "\n".join(lines[:20])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=_TEXT_DELIMITERS)
    except csv.Error as exc:
        raise ValueError(
            f"无法识别 {path} 的分隔符；TXT 必须是带表头的分隔符文本，"
            "支持逗号、Tab、分号或竖线分隔。"
        ) from exc
    return dialect.delimiter


def _validate_text_headers(path: str, headers: list[str]) -> None:
    """校验分隔文本表头，避免后续按列错读。"""
    if not headers:
        raise ValueError(f"{path} 表头为空")
    if len(headers) <= 1:
        raise ValueError(
            f"{path} 只识别到 1 列；TXT 必须是逗号、Tab、分号或竖线分隔的表格文本。"
        )
    empty_indexes = [str(i + 1) for i, h in enumerate(headers) if not clean(h)]
    if empty_indexes:
        raise ValueError(f"{path} 表头存在空字段，列号: {', '.join(empty_indexes)}")
    seen: set[str] = set()
    duplicates: list[str] = []
    for h in headers:
        if h in seen and h not in duplicates:
            duplicates.append(h)
        seen.add(h)
    if duplicates:
        raise ValueError(f"{path} 表头存在重复字段: {duplicates}")


def read_delimited_text(path: str, strict: bool = False) -> tuple[list[str], list[list[str]]]:
    """读取带表头的分隔文本文件，返回 (headers, rows)。"""
    text = _read_text(path)
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError(f"{path} 文件为空")

    delimiter = _sniff_delimiter(path, lines)
    parsed_rows = list(csv.reader(lines, delimiter=delimiter))
    headers = [clean(h) for h in parsed_rows[0]]
    _validate_text_headers(path, headers)

    rows = parsed_rows[1:]
    if strict:
        expected = len(headers)
        bad_rows = [
            (line_no, len(row))
            for line_no, row in enumerate(rows, start=2)
            if len(row) != expected
        ]
        if bad_rows:
            detail = ", ".join(
                f"第{line_no}行{width}列" for line_no, width in bad_rows[:10]
            )
            raise ValueError(
                f"{path} 行列数不一致，表头为 {expected} 列，异常行: {detail}"
            )
    return headers, rows


def read_csv(csv_path: str) -> tuple[list[str], list[list[str]]]:
    """读取 CSV 文件，返回 (headers, rows)。自动尝试 utf-8-sig / utf-8 / gbk / gb18030。"""
    text = _read_text(csv_path)
    reader = csv.reader(io.StringIO(text))
    headers = next(reader)
    return headers, list(reader)


def _validate_numeric_columns(path: str, headers: list[str], rows: list[list[str]]) -> None:
    """校验商业 AB 关键数值列，避免 TXT 错列后继续生成。"""
    numeric_fields = ("eshow", "click", "charge", "tcharge", "conv")
    indexes = [headers.index(field) for field in numeric_fields if field in headers]
    bad_values: list[str] = []
    for row_no, row in enumerate(rows, start=2):
        for col_idx in indexes:
            raw = clean(row[col_idx])
            if not raw or raw == "-":
                continue
            try:
                float(raw)
            except ValueError:
                bad_values.append(f"第{row_no}行 {headers[col_idx]}={raw!r}")
                if len(bad_values) >= 10:
                    break
        if len(bad_values) >= 10:
            break
    if bad_values:
        raise ValueError(f"{path} 数值字段存在非法值: {', '.join(bad_values)}")


def read_txt(txt_path: str) -> tuple[list[str], list[list[str]]]:
    """读取 TXT 分隔文本文件，并执行严格结构校验。"""
    headers, rows = read_delimited_text(txt_path, strict=True)
    _validate_numeric_columns(txt_path, headers, rows)
    return headers, rows


# ── XLSX 读取（零外部依赖，解析 OOXML ZIP） ───────────────────────

_SHEET_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_COL_RE = re.compile(r"([A-Z]+)\d+")


def _col_letter_to_idx(col: str) -> int:
    """列字母 → 0-based 索引: A→0, B→1, ..., Z→25, AA→26。"""
    result = 0
    for ch in col:
        result = result * 26 + (ord(ch) - ord("A") + 1)
    return result - 1


def _parse_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    """解析 xl/sharedStrings.xml，返回共享字符串列表。"""
    try:
        data = zf.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ET.fromstring(data)
    strings: list[str] = []
    for si in root.iter(f"{_SHEET_NS}si"):
        # <si><t>text</t></si> 或 <si><r><t>text</t></r>...</si>
        parts: list[str] = []
        for t in si.iter(f"{_SHEET_NS}t"):
            parts.append(t.text or "")
        strings.append("".join(parts))
    return strings


_WB_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_WB_REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_PKG_REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def _parse_sheet_map(zf: zipfile.ZipFile) -> dict[str, str]:
    """解析 workbook.xml + workbook.xml.rels，返回 {sheet名称: zip内路径}。"""
    # 1. workbook.xml: 获取 sheetId → name 和 rId
    try:
        wb_data = zf.read("xl/workbook.xml")
    except KeyError:
        return {}
    wb_root = ET.fromstring(wb_data)
    # sheet 元素在 <sheets> 下，可能带命名空间也可能不带
    rid_to_name: dict[str, str] = {}
    for sheet_el in wb_root.iter(f"{_WB_NS}sheet"):
        name = sheet_el.get("name", "")
        rid = sheet_el.get(f"{_WB_REL_NS}id") or sheet_el.get("r:id", "")
        if name and rid:
            rid_to_name[rid] = name

    # 2. workbook.xml.rels: 获取 rId → 相对路径
    try:
        rels_data = zf.read("xl/_rels/workbook.xml.rels")
    except KeyError:
        return {}
    rels_root = ET.fromstring(rels_data)
    name_to_path: dict[str, str] = {}
    for rel in rels_root.iter(f"{_PKG_REL_NS}Relationship"):
        rid = rel.get("Id", "")
        target = rel.get("Target", "")
        if rid in rid_to_name:
            # target 可能是相对路径如 "worksheets/sheet1.xml"
            if not target.startswith("xl/"):
                target = "xl/" + target
            name_to_path[rid_to_name[rid]] = target
    return name_to_path


def _find_first_sheet_path(zf: zipfile.ZipFile) -> str:
    """找到第一个有数据的工作表路径。

    优先选择包含非空 sheetData 的 sheet，避免选中透视表占位的空 sheet。
    """
    sheet_paths = sorted(
        n for n in zf.namelist()
        if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")
    )
    if not sheet_paths:
        raise ValueError("xlsx 中未找到工作表")

    # 优先找有数据行的 sheet
    for sp in sheet_paths:
        data = zf.read(sp)
        root = ET.fromstring(data)
        sd = root.find(f"{_SHEET_NS}sheetData")
        if sd is not None and len(sd) > 0:
            return sp

    # 都没数据行，返回第一个
    return sheet_paths[0]


def read_xlsx(xlsx_path: str, sheet_name: str | None = None) -> tuple[list[str], list[list[str]]]:
    """读取 xlsx 文件指定工作表，返回 (headers, rows)。

    sheet_name: 指定 sheet 名称（如 "原始数据"）。None 时自动找第一个有数据的 sheet。
    零外部依赖：通过 zipfile + xml.etree 解析 OOXML。
    所有单元格值转为字符串，与 CSV 读取结果格式一致。
    """
    with zipfile.ZipFile(xlsx_path, "r") as zf:
        shared = _parse_shared_strings(zf)

        if sheet_name is not None:
            sheet_map = _parse_sheet_map(zf)
            if sheet_name not in sheet_map:
                available = list(sheet_map.keys())
                raise ValueError(
                    f"xlsx 中未找到 sheet '{sheet_name}'，可用 sheet: {available}"
                )
            sheet_path = sheet_map[sheet_name]
        else:
            sheet_path = _find_first_sheet_path(zf)

        sheet_data = zf.read(sheet_path)

    root = ET.fromstring(sheet_data)
    sheet_data_el = root.find(f"{_SHEET_NS}sheetData")
    if sheet_data_el is None:
        raise ValueError(f"xlsx 工作表中无 sheetData: {xlsx_path}")

    all_rows: list[list[str]] = []
    for row_el in sheet_data_el.iter(f"{_SHEET_NS}row"):
        cells: dict[int, str] = {}
        max_col = -1
        for c_el in row_el.iter(f"{_SHEET_NS}c"):
            ref = c_el.get("r", "")
            m = _COL_RE.match(ref)
            if not m:
                continue
            col_idx = _col_letter_to_idx(m.group(1))
            max_col = max(max_col, col_idx)

            v_el = c_el.find(f"{_SHEET_NS}v")
            v_text = v_el.text if v_el is not None else ""
            cell_type = c_el.get("t", "")

            if cell_type == "s":
                # 共享字符串引用
                val = shared[int(v_text)] if v_text else ""
            elif cell_type == "inlineStr":
                is_el = c_el.find(f"{_SHEET_NS}is")
                if is_el is not None:
                    parts = [t.text or "" for t in is_el.iter(f"{_SHEET_NS}t")]
                    val = "".join(parts)
                else:
                    val = ""
            else:
                val = v_text or ""

            cells[col_idx] = val

        if max_col >= 0:
            row = [cells.get(i, "") for i in range(max_col + 1)]
            all_rows.append(row)

    if not all_rows:
        raise ValueError(f"xlsx 工作表为空: {xlsx_path}")

    headers = all_rows[0]
    num_cols = len(headers)

    # 统一行宽度：补齐短行，截断超宽行
    data_rows = []
    for r in all_rows[1:]:
        if len(r) < num_cols:
            r = r + [""] * (num_cols - len(r))
        elif len(r) > num_cols:
            r = r[:num_cols]
        data_rows.append(r)

    return headers, data_rows


# ── 统一读取调度 ──────────────────────────────────────────────────

def read_file(path: str, sheet_name: str | None = None) -> tuple[list[str], list[list[str]]]:
    """根据文件扩展名自动选择 CSV、TXT 或 XLSX 读取。

    sheet_name: 仅对 xlsx 有效，指定要读取的 sheet 名称。
    """
    lower_path = path.lower()
    if lower_path.endswith((".xlsx", ".xls")):
        return read_xlsx(path, sheet_name=sheet_name)
    if lower_path.endswith(".txt"):
        return read_txt(path)
    if lower_path.endswith(".csv"):
        return read_csv(path)
    raise ValueError(f"不支持的输入文件格式: {path}（仅支持 .csv/.txt/.xlsx/.xls）")


def read_files(paths: list[str], xlsx_sheet_name: str | None = None) -> tuple[list[str], list[list[str]]]:
    """读取多个 CSV/TXT/XLSX 文件并拼接，校验表头一致性。

    xlsx_sheet_name: 对所有 xlsx 文件统一指定读取的 sheet 名称。None 时自动找有数据的 sheet。
    返回 (headers, all_rows)。文件按传入顺序拼接。
    """
    if len(paths) == 1:
        return read_file(paths[0], sheet_name=xlsx_sheet_name)

    headers, all_rows = read_file(paths[0], sheet_name=xlsx_sheet_name)
    for path in paths[1:]:
        h, rows = read_file(path, sheet_name=xlsx_sheet_name)
        if h != headers:
            raise ValueError(
                f"表头不一致:\n  {paths[0]}: {headers}\n  {path}: {h}"
            )
        all_rows.extend(rows)
    return headers, all_rows


def read_csvs(csv_paths: list[str]) -> tuple[list[str], list[list[str]]]:
    """兼容旧接口，内部调用 read_files。"""
    return read_files(csv_paths)


def suggest_field_mapping(
    headers: list[str], required: list[str]
) -> dict[str, list[str]]:
    """对每个缺失的必需字段，从 headers 中找出包含其名（子串、大小写不敏感）的候选。

    已存在于 required 中的字段名不会被作为候选（避免如 `charge` 错配到 `tcharge`）。
    返回 {missing_field: [candidate_header, ...]}，仅包含至少有一个候选的缺失字段。
    """
    headers_set = set(headers)
    required_set = set(required)
    result: dict[str, list[str]] = {}
    for field_name in required:
        if field_name in headers_set:
            continue
        needle = field_name.lower()
        candidates = [
            h for h in headers
            if needle in h.lower() and h not in required_set
        ]
        if candidates:
            result[field_name] = candidates
    return result


def _infer_column_type(rows: list[list[str]], col_idx: int, sample_size: int = 500) -> str:
    """从样本值推断列类型，返回 'int' / 'float' / 'str'。"""
    saw_numeric = False
    saw_float = False
    for r in rows[:sample_size]:
        if col_idx >= len(r):
            continue
        v = clean(r[col_idx])
        if not v or v == "-":
            continue
        try:
            int(v)
            saw_numeric = True
            continue
        except ValueError:
            pass
        try:
            float(v)
            saw_numeric = True
            saw_float = True
            continue
        except ValueError:
            return "str"
    if not saw_numeric:
        return "str"
    return "float" if saw_float else "int"


def align_config_to_headers(
    config: PivotConfig, headers: list[str], rows: list[list[str]]
) -> None:
    """原地修改 config.columns 使其与 CSV headers 顺序对齐。

    规则：
    - config 声明的列必须全部出现在 headers 中，否则抛 ValueError
    - headers 中未在 config 声明的字段自动追加为 ColumnDef（类型推断、nullable=True、shared_items_type='auto'）
    - config.columns 重排后与 headers 一一对应（位置一致），确保后续按位置读取正确
    """
    known = {c.name: c for c in config.columns}
    missing = [c.name for c in config.columns if c.name not in headers]
    if missing:
        raise ValueError(
            f"缺少预设声明的字段: {missing}（数据字段: {headers}）"
        )
    new_columns: list[ColumnDef] = []
    for i, h in enumerate(headers):
        if h in known:
            new_columns.append(known[h])
        else:
            new_columns.append(
                ColumnDef(
                    name=h,
                    type=_infer_column_type(rows, i),
                    nullable=True,
                    shared_items_type="auto",
                )
            )
    config.columns = new_columns


def _unique_ordered(rows: list[list[str]], col_idx: int, convert=None) -> list:
    """按首次出现顺序收集某列的去重值。跳过无法转换的值（如 '-'）。

    对字符串枚举字段使用 casefold 键去重：Excel 透视表的 sharedItems 做大小写
    不敏感比较，若同一列同时出现 "leftslide" 和 "leftSlide" 会被判定为重复
    枚举项，Excel 会删除整个 pivotTable。因此 str 类型按 casefold 去重，但
    保留首次出现的原始大小写作为展示值。
    """
    if convert is None:
        convert = str
    is_str = convert is str
    seen: set = set()
    result: list = []
    for r in rows:
        raw = clean(r[col_idx])
        if not raw:
            continue
        try:
            v = convert(raw)
        except (ValueError, TypeError):
            continue
        key = v.casefold() if is_str else v
        if key not in seen:
            seen.add(key)
            result.append(v)
    return result


def _col_stats(rows: list[list[str]], col_idx: int, convert=float) -> list:
    """收集某列的非空数值列表（用于 min/max 统计）。跳过无法转换的值（如 '-'）。"""
    result = []
    for r in rows:
        v = clean(r[col_idx])
        if not v:
            continue
        try:
            result.append(int(float(v)) if convert is int else convert(v))
        except (ValueError, TypeError):
            pass
    return result


def analyze_fields(config: PivotConfig, headers: list[str], rows: list[list[str]]) -> FieldMaps:
    """根据配置分析 CSV 数据，产出 FieldMaps。"""
    fm = FieldMaps(headers=headers, rows=rows)

    for i, col_def in enumerate(config.columns):
        # 检查是否有空值
        fm.has_blanks[i] = any(clean(r[i]) == "" for r in rows)

        sit = col_def.shared_items_type
        if sit == "auto":
            sit = "enumerated" if col_def.type == "str" else "range"

        if sit == "enumerated":
            if col_def.type == "int":
                items = _unique_ordered(rows, i, int)
                fm.enumerated_items[i] = items
                fm.item_index_maps[i] = {v: idx for idx, v in enumerate(items)}
            else:
                items = _unique_ordered(rows, i)
                fm.enumerated_items[i] = items
                # 字符串枚举：item_index_maps 按 casefold 键存储（Excel 大小写不敏感，
                # _unique_ordered 已用 casefold 去重，此处需让 _encode_cell 按相同
                # 规则查表，避免原始大小写与枚举项不完全一致时查不到索引）
                fm.item_index_maps[i] = {v.casefold(): idx for idx, v in enumerate(items)}

            # Strategy Z: 字符串枚举字段若有空值，把 "" 作为显式枚举项。
            # Excel 不接受"字符串枚举 + containsBlank + <m/> 记录"的组合（会删除
            # 整个 pivotTable 部件），但接受纯枚举含 <s v=""/>。转换后 has_blanks
            # 清零，使得 sharedItems 不加 containsBlank、pivotField items 不加
            # <item t="blank"/>，records 统一用 <x v="idx"/>。
            if col_def.type == "str" and fm.has_blanks.get(i, False):
                if "" not in fm.item_index_maps[i]:
                    fm.enumerated_items[i].append("")
                    fm.item_index_maps[i][""] = len(fm.enumerated_items[i]) - 1
                fm.has_blanks[i] = False

        if col_def.type in ("int", "float"):
            convert = int if col_def.type == "int" else float
            vals = _col_stats(rows, i, convert)
            if vals:
                fm.stats[i] = (min(vals), max(vals))
            else:
                fm.stats[i] = (0, 0)

        # mixed 类型 (如 mt_id): 同时收集数值统计
        if sit == "mixed":
            nums = []
            for r in rows:
                v = clean(r[i])
                if v and "#" not in v and v.strip():
                    try:
                        nums.append(int(v))
                    except ValueError:
                        pass
            if nums:
                fm.stats[i] = (min(nums), max(nums))
            else:
                fm.stats[i] = (0, 0)

    return fm
