"""Excel PivotTable OOXML 结构闸门。

这个检查器只依赖标准库，专门拦截 zip/openpyxl 可能放过、但 Excel
打开时会提示修复的 PivotTable 结构问题。
"""

from __future__ import annotations

import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
RANGE_REF_RE = re.compile(r"^\$?[A-Z]+\$?(\d+):\$?[A-Z]+\$?(\d+)$")


class PivotOoxmlError(ValueError):
    """PivotTable OOXML 结构校验失败。"""


def _read_xml(zf: zipfile.ZipFile, name: str, errors: list[str]) -> ET.Element | None:
    try:
        return ET.fromstring(zf.read(name))
    except KeyError:
        errors.append(f"缺少 OOXML 部件: {name}")
    except ET.ParseError as exc:
        errors.append(f"{name} XML 解析失败: {exc}")
    return None


def _int_attr(el: ET.Element | None, attr: str, default: int = 0) -> int:
    if el is None:
        return default
    try:
        return int(el.get(attr, str(default)))
    except ValueError:
        return default


def _children(el: ET.Element | None, tag: str) -> list[ET.Element]:
    if el is None:
        return []
    return list(el.findall(f"{NS}{tag}"))


def _raw_pivot_fields(pivot_xml: str) -> list[str]:
    match = re.search(r"<pivotFields\b[^>]*>(.*?)</pivotFields>", pivot_xml, re.S)
    if not match:
        return []
    return re.findall(r"<pivotField\b[^>]*(?:/>|>.*?</pivotField>)", match.group(1), re.S)


def _validate_counts(label: str, parent: ET.Element | None, child_tag: str, errors: list[str]) -> None:
    if parent is None:
        return
    children = _children(parent, child_tag)
    declared = _int_attr(parent, "count", len(children))
    if declared != len(children):
        errors.append(f"{label} count={declared}，实际 {child_tag} 数量={len(children)}")


def _validate_cache(cache_root: ET.Element | None, errors: list[str]) -> tuple[list[ET.Element], set[int]]:
    if cache_root is None:
        return [], set()

    if cache_root.get("refreshOnLoad") != "1":
        errors.append("pivotCacheDefinition 缺少 refreshOnLoad=\"1\"")

    cache_fields_parent = cache_root.find(f"{NS}cacheFields")
    cache_fields = _children(cache_fields_parent, "cacheField")
    _validate_counts("cacheFields", cache_fields_parent, "cacheField", errors)

    calculated_indices: set[int] = set()
    for idx, field in enumerate(cache_fields):
        if field.get("databaseField") == "0":
            calculated_indices.add(idx)

        shared_items = field.find(f"{NS}sharedItems")
        if shared_items is None:
            continue

        string_values = [s.get("v", "") for s in shared_items.findall(f"{NS}s")]
        folded = [value.casefold() for value in string_values]
        if len(folded) != len(set(folded)):
            errors.append(f"cacheField {field.get('name')!r} 的字符串枚举项存在大小写重复")

    return cache_fields, calculated_indices


def _validate_pivot_fields(
    pivot_root: ET.Element | None,
    pivot_xml: str,
    cache_fields: list[ET.Element],
    calculated_indices: set[int],
    errors: list[str],
) -> None:
    if pivot_root is None:
        return

    pivot_fields_parent = pivot_root.find(f"{NS}pivotFields")
    pivot_fields = _children(pivot_fields_parent, "pivotField")
    _validate_counts("pivotFields", pivot_fields_parent, "pivotField", errors)

    if cache_fields and len(pivot_fields) != len(cache_fields):
        errors.append(f"pivotFields 数量 {len(pivot_fields)} 与 cacheFields 数量 {len(cache_fields)} 不一致")

    for idx, cache_field in enumerate(cache_fields):
        if idx >= len(pivot_fields):
            continue
        shared_items = cache_field.find(f"{NS}sharedItems")
        if shared_items is None or "count" not in shared_items.attrib:
            continue
        items = pivot_fields[idx].find(f"{NS}items")
        if items is None:
            errors.append(f"枚举 cacheField {cache_field.get('name')!r} 缺少 pivotField/items")
            continue
        expected = _int_attr(shared_items, "count") + 1
        if shared_items.get("containsBlank") == "1":
            expected += 1
        actual = _int_attr(items, "count", len(_children(items, "item")))
        if expected != actual:
            errors.append(
                f"pivotField {cache_field.get('name')!r} items count={actual}，期望 {expected}"
            )
        if not any(item.get("t") == "default" for item in _children(items, "item")):
            errors.append(f"pivotField {cache_field.get('name')!r} items 缺少 default item")

    raw_fields = _raw_pivot_fields(pivot_xml)
    for idx in calculated_indices:
        if idx >= len(raw_fields):
            continue
        raw = raw_fields[idx]
        attrs_match = re.match(r"<pivotField\b([^>]*)", raw, re.S)
        attrs = attrs_match.group(1) if attrs_match else ""
        ordered = [
            'dragToRow="0"',
            'dragToCol="0"',
            'dragToPage="0"',
            'showAll="0"',
            'defaultSubtotal="0"',
        ]
        positions = [attrs.find(token) for token in ordered]
        if any(pos < 0 for pos in positions) or positions != sorted(positions):
            errors.append(f"计算字段 pivotField[{idx}] 属性顺序或必需属性不符合兼容约束")
        data_pos = attrs.find('dataField="1"')
        if data_pos >= 0 and data_pos > positions[0]:
            errors.append(f"计算字段 pivotField[{idx}] dataField 属性必须位于 dragToRow 之前")


def _validate_layout(pivot_root: ET.Element | None, pivot_xml: str, errors: list[str]) -> None:
    if pivot_root is None:
        return

    data_fields = pivot_root.find(f"{NS}dataFields")
    data_count = _int_attr(data_fields, "count", len(_children(data_fields, "dataField")))
    _validate_counts("dataFields", data_fields, "dataField", errors)

    col_fields = pivot_root.find(f"{NS}colFields")
    col_items = pivot_root.find(f"{NS}colItems")
    has_col_fields = col_fields is not None
    has_data_col = any(field.get("x") == "-2" for field in _children(col_fields, "field"))

    if data_count > 1:
        if not has_data_col:
            errors.append("多个 dataFields 横向展开时 colFields 必须包含 <field x=\"-2\"/>")
        if col_items is None:
            errors.append("多个 dataFields 横向展开时缺少 colItems")
        elif _int_attr(col_items, "count", len(_children(col_items, "i"))) != data_count:
            errors.append(f"colItems count 与 dataFields count 不一致: {col_items.get('count')} vs {data_count}")

    page_fields = pivot_root.find(f"{NS}pageFields")
    pivot_fields = _children(pivot_root.find(f"{NS}pivotFields"), "pivotField")
    axis_page_indices = {idx for idx, field in enumerate(pivot_fields) if field.get("axis") == "axisPage"}
    page_field_children = _children(page_fields, "pageField")

    if axis_page_indices and page_fields is None:
        errors.append("存在 axisPage pivotField，但缺少 pageFields")
    if page_fields is not None:
        _validate_counts("pageFields", page_fields, "pageField", errors)
        page_field_indices = set()
        for field in page_field_children:
            try:
                fld = int(field.get("fld", ""))
                page_field_indices.add(fld)
            except ValueError:
                errors.append(f"pageField fld 非法: {field.get('fld')!r}")
                continue
            if field.get("hier") != "-1":
                errors.append(f"pageField fld={fld} 缺少 hier=\"-1\"")
        if page_field_indices != axis_page_indices:
            errors.append(
                f"pageFields fld 集合 {sorted(page_field_indices)} 与 axisPage 集合 {sorted(axis_page_indices)} 不一致"
            )

    location = pivot_root.find(f"{NS}location")
    if location is None:
        errors.append("pivotTableDefinition 缺少 location")
    else:
        page_field_count = len(axis_page_indices)
        expected_first_data_row = "1" if page_field_count else ("2" if has_col_fields else "1")
        if location.get("firstDataRow") != expected_first_data_row:
            errors.append(
                f"location firstDataRow={location.get('firstDataRow')}，期望 {expected_first_data_row}"
            )

        # 页面筛选区位于透视主体上方，纵向 N 个筛选字段至少占 N 行，
        # 并与主体间隔 1 行。location@ref 只覆盖主体，不能与筛选区重叠。
        ref = location.get("ref", "")
        match = RANGE_REF_RE.fullmatch(ref)
        if match is None:
            errors.append(f"location ref 格式非法: {ref!r}")
        else:
            first_row, last_row = (int(value) for value in match.groups())
            min_first_row = page_field_count + 2 if page_field_count else 1
            if first_row < min_first_row:
                errors.append(
                    f"location ref={ref} 与 {page_field_count} 个 pageFields 重叠，"
                    f"主体首行不得早于 {min_first_row}"
                )

            row_items = pivot_root.find(f"{NS}rowItems")
            row_item_count = _int_attr(
                row_items, "count", len(_children(row_items, "i")) or 1
            )
            first_data_row = _int_attr(location, "firstDataRow")
            expected_last_row = first_row + first_data_row + row_item_count - 1
            if last_row != expected_last_row:
                errors.append(
                    f"location ref={ref} 高度与 firstDataRow/rowItems 不一致，"
                    f"末行应为 {expected_last_row}"
                )

        if page_field_count:
            if location.get("rowPageCount") != str(page_field_count):
                errors.append(
                    f"location rowPageCount={location.get('rowPageCount')}，"
                    f"期望 {page_field_count}"
                )
            if location.get("colPageCount") != "1":
                errors.append(
                    f"location colPageCount={location.get('colPageCount')}，期望 1"
                )

    if "<pageFields" in pivot_xml and "<dataFields" in pivot_xml:
        if pivot_xml.index("<pageFields") > pivot_xml.index("<dataFields"):
            errors.append("pageFields 必须位于 dataFields 之前")
    if "<colItems" in pivot_xml and "<pageFields" in pivot_xml:
        if pivot_xml.index("<colItems") > pivot_xml.index("<pageFields"):
            errors.append("pageFields 必须位于 colItems 之后")


def validate_pivot_xlsx(path: str | Path) -> list[str]:
    """返回 PivotTable OOXML 结构错误列表；空列表表示通过。"""
    errors: list[str] = []
    path = Path(path)
    required_parts = [
        "xl/workbook.xml",
        "xl/pivotCache/pivotCacheDefinition1.xml",
        "xl/pivotCache/pivotCacheRecords1.xml",
        "xl/pivotTables/pivotTable1.xml",
        "xl/worksheets/_rels/sheet1.xml.rels",
        "xl/pivotTables/_rels/pivotTable1.xml.rels",
        "xl/pivotCache/_rels/pivotCacheDefinition1.xml.rels",
    ]

    try:
        with zipfile.ZipFile(path, "r") as zf:
            names = set(zf.namelist())
            for part in required_parts:
                if part not in names:
                    errors.append(f"缺少 OOXML 部件: {part}")

            cache_root = _read_xml(zf, "xl/pivotCache/pivotCacheDefinition1.xml", errors)
            pivot_root = _read_xml(zf, "xl/pivotTables/pivotTable1.xml", errors)
            try:
                pivot_xml = zf.read("xl/pivotTables/pivotTable1.xml").decode("utf-8")
            except KeyError:
                pivot_xml = ""
    except zipfile.BadZipFile:
        return [f"不是合法 xlsx zip 文件: {path}"]

    cache_fields, calculated_indices = _validate_cache(cache_root, errors)
    _validate_pivot_fields(pivot_root, pivot_xml, cache_fields, calculated_indices, errors)
    _validate_layout(pivot_root, pivot_xml, errors)
    return errors


def assert_valid_pivot_xlsx(path: str | Path) -> None:
    errors = validate_pivot_xlsx(path)
    if errors:
        detail = "\n  - ".join(errors)
        raise PivotOoxmlError(f"PivotTable OOXML 兼容性校验失败:\n  - {detail}")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print("用法: python -m pivot_tool.ooxml_guard <file.xlsx>", file=sys.stderr)
        return 2
    errors = validate_pivot_xlsx(argv[0])
    if errors:
        print("PivotTable OOXML 兼容性校验失败:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print(f"PivotTable OOXML 兼容性校验通过: {argv[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
