"""Excel PivotTable OOXML 结构闸门。

这个检查器只依赖标准库，专门拦截 zip/openpyxl 可能放过、但 Excel
打开时会提示修复的 PivotTable 结构问题。
"""

from __future__ import annotations

import posixpath
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
DOC_REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PKG_REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
CONTENT_TYPES_NS = "{http://schemas.openxmlformats.org/package/2006/content-types}"
PIVOT_CACHE_REL = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
    "pivotCacheDefinition"
)
PIVOT_RECORDS_REL = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
    "pivotCacheRecords"
)
PIVOT_TABLE_REL = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/pivotTable"
)
STYLES_REL = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles"
)
STYLES_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"
)
RANGE_REF_RE = re.compile(r"^\$?[A-Z]+\$?(\d+):\$?[A-Z]+\$?(\d+)$")
PIVOT_PART_RE = re.compile(r"^xl/pivotTables/pivotTable\d+\.xml$")
STYLE_CHILD_ORDER = {
    name: index
    for index, name in enumerate(
        (
            "numFmts",
            "fonts",
            "fills",
            "borders",
            "cellStyleXfs",
            "cellXfs",
            "cellStyles",
            "dxfs",
            "tableStyles",
            "colors",
            "extLst",
        )
    )
}


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


def _rels_part(source_part: str) -> str:
    """返回某个 OOXML 部件对应的关系部件路径。"""
    parent, name = posixpath.split(source_part)
    return posixpath.join(parent, "_rels", f"{name}.rels")


def _resolve_target(source_part: str, target: str) -> str:
    """按 OOXML 关系规则把相对 Target 解析为 zip 内部路径。"""
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join(posixpath.dirname(source_part), target))


def _relationships(
    zf: zipfile.ZipFile,
    source_part: str,
    errors: list[str],
    *,
    required: bool,
) -> dict[str, tuple[str, str]]:
    """读取部件关系，返回 ``rId -> (类型, 目标部件)``。"""
    rels_part = _rels_part(source_part)
    if rels_part not in zf.namelist():
        if required:
            errors.append(f"缺少 OOXML 关系部件: {rels_part}")
        return {}

    root = _read_xml(zf, rels_part, errors)
    relationships: dict[str, tuple[str, str]] = {}
    if root is None:
        return relationships

    for relation in root.findall(f"{PKG_REL_NS}Relationship"):
        rel_id = relation.get("Id", "")
        rel_type = relation.get("Type", "")
        target = relation.get("Target", "")
        if not rel_id or not target:
            errors.append(f"{rels_part} 存在缺少 Id 或 Target 的关系")
            continue
        if rel_id in relationships:
            errors.append(f"{rels_part} 存在重复关系 Id={rel_id}")
            continue
        relationships[rel_id] = (
            rel_type,
            _resolve_target(source_part, target),
        )
    return relationships


def _only_relationship_target(
    source_part: str,
    relationships: dict[str, tuple[str, str]],
    expected_type: str,
    errors: list[str],
) -> str | None:
    """取得指定类型的唯一关系目标，并报告缺失或重复。"""
    targets = [target for rel_type, target in relationships.values() if rel_type == expected_type]
    if len(targets) != 1:
        errors.append(
            f"{source_part} 的 {expected_type.rsplit('/', 1)[-1]} 关系数量为 "
            f"{len(targets)}，期望 1"
        )
        return None
    return targets[0]


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


def _validate_index_attr(
    element: ET.Element,
    label: str,
    attr: str,
    limit: int,
    errors: list[str],
) -> None:
    """校验样式索引，避免 Excel 因越界引用修复整个工作簿。"""
    raw_value = element.get(attr)
    if raw_value is None:
        errors.append(f"{label} 缺少 {attr}")
        return
    try:
        value = int(raw_value)
    except ValueError:
        errors.append(f"{label} {attr} 非法: {raw_value!r}")
        return
    if value < 0 or value >= limit:
        errors.append(f"{label} {attr}={value} 越界，可用数量={limit}")


def _validate_styles(
    zf: zipfile.ZipFile,
    names: set[str],
    workbook_rels: dict[str, tuple[str, str]],
    errors: list[str],
) -> None:
    """校验 workbook 样式关系、Content Type 和 styles.xml 内部引用。"""
    styles_part = _only_relationship_target(
        "xl/workbook.xml",
        workbook_rels,
        STYLES_REL,
        errors,
    )

    content_types = _read_xml(zf, "[Content_Types].xml", errors)
    if content_types is not None:
        style_overrides = [
            override
            for override in content_types.findall(f"{CONTENT_TYPES_NS}Override")
            if override.get("ContentType") == STYLES_CONTENT_TYPE
        ]
        if len(style_overrides) != 1:
            errors.append(
                "[Content_Types].xml 的 styles Content Type 声明数量为 "
                f"{len(style_overrides)}，期望 1"
            )
        elif styles_part is not None:
            declared_part = style_overrides[0].get("PartName", "").lstrip("/")
            if declared_part != styles_part:
                errors.append(
                    "styles 关系目标与 Content Type 声明不一致: "
                    f"{styles_part} vs {declared_part}"
                )

    if styles_part is None:
        return
    if styles_part not in names:
        errors.append(f"workbook styles 关系指向不存在的部件: {styles_part}")
        return

    styles_root = _read_xml(zf, styles_part, errors)
    if styles_root is None:
        return
    if styles_root.tag != f"{NS}styleSheet":
        errors.append(f"{styles_part} 根元素不是 styleSheet")
        return

    # SpreadsheetML 对 styleSheet 子元素有固定顺序；顺序错误时 Excel 会修复文件。
    previous_rank = -1
    for child in styles_root:
        local_name = child.tag.rsplit("}", 1)[-1]
        rank = STYLE_CHILD_ORDER.get(local_name)
        if rank is None:
            continue
        if rank < previous_rank:
            errors.append(f"{styles_part} 子元素顺序非法: {local_name}")
            break
        previous_rank = rank

    collections: dict[str, list[ET.Element]] = {}
    for parent_tag, child_tag in (
        ("fonts", "font"),
        ("fills", "fill"),
        ("borders", "border"),
        ("cellStyleXfs", "xf"),
        ("cellXfs", "xf"),
        ("cellStyles", "cellStyle"),
    ):
        parent = styles_root.find(f"{NS}{parent_tag}")
        if parent is None:
            errors.append(f"{styles_part} 缺少 {parent_tag}")
            collections[parent_tag] = []
            continue
        if "count" not in parent.attrib:
            errors.append(f"{styles_part} {parent_tag} 缺少 count")
        _validate_counts(parent_tag, parent, child_tag, errors)
        collections[parent_tag] = _children(parent, child_tag)

    for optional_tag, child_tag in (("dxfs", "dxf"), ("tableStyles", "tableStyle")):
        parent = styles_root.find(f"{NS}{optional_tag}")
        if parent is not None:
            _validate_counts(optional_tag, parent, child_tag, errors)

    fonts = collections["fonts"]
    fills = collections["fills"]
    borders = collections["borders"]
    style_xfs = collections["cellStyleXfs"]
    cell_xfs = collections["cellXfs"]
    cell_styles = collections["cellStyles"]

    for group_name, xfs in (("cellStyleXfs", style_xfs), ("cellXfs", cell_xfs)):
        for index, xf in enumerate(xfs):
            label = f"{group_name}/xf[{index}]"
            _validate_index_attr(xf, label, "fontId", len(fonts), errors)
            _validate_index_attr(xf, label, "fillId", len(fills), errors)
            _validate_index_attr(xf, label, "borderId", len(borders), errors)
            if group_name == "cellXfs":
                _validate_index_attr(xf, label, "xfId", len(style_xfs), errors)

    for index, style in enumerate(cell_styles):
        _validate_index_attr(
            style,
            f"cellStyles/cellStyle[{index}]",
            "xfId",
            len(style_xfs),
            errors,
        )

    normal_styles = [style for style in cell_styles if style.get("name") == "Normal"]
    if len(normal_styles) != 1:
        errors.append(f"cellStyles 中 Normal 命名样式数量为 {len(normal_styles)}，期望 1")
    else:
        normal = normal_styles[0]
        if normal.get("xfId") != "0" or normal.get("builtinId") != "0":
            errors.append(
                "Normal 命名样式必须声明 xfId=\"0\" builtinId=\"0\""
            )


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
        # 仅校验 items@count 还不够：Excel 实际按子节点解析，声明值与内容
        # 不一致时旧版 Mac Excel 可能在加载 pivotTable 时直接崩溃。
        _validate_counts(
            f"pivotField {cache_field.get('name')!r} items",
            items,
            "item",
            errors,
        )
        expected = _int_attr(shared_items, "count") + 1
        if shared_items.get("containsBlank") == "1":
            expected += 1
        actual = len(_children(items, "item"))
        if expected != actual:
            errors.append(
                f"pivotField {cache_field.get('name')!r} items 实际数量={actual}，期望 {expected}"
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

    try:
        with zipfile.ZipFile(path, "r") as zf:
            names = set(zf.namelist())
            bad_member = zf.testzip()
            if bad_member:
                errors.append(f"ZIP 成员校验失败: {bad_member}")

            workbook_part = "xl/workbook.xml"
            workbook_root = _read_xml(zf, workbook_part, errors)
            workbook_rels = _relationships(
                zf,
                workbook_part,
                errors,
                required=True,
            )
            _validate_styles(zf, names, workbook_rels, errors)

            # workbook 的 cacheId 是 PivotTable 与 cache definition 之间的权威映射。
            # 多业务文件允许部件编号不连续，因此只能沿关系解析实际目标。
            workbook_caches: dict[int, str] = {}
            pivot_caches = (
                workbook_root.find(f"{NS}pivotCaches")
                if workbook_root is not None
                else None
            )
            for cache in _children(pivot_caches, "pivotCache"):
                raw_cache_id = cache.get("cacheId", "")
                try:
                    cache_id = int(raw_cache_id)
                except ValueError:
                    errors.append(f"workbook pivotCache cacheId 非法: {raw_cache_id!r}")
                    continue
                if cache_id in workbook_caches:
                    errors.append(f"workbook 存在重复 pivotCache cacheId={cache_id}")
                    continue

                rel_id = cache.get(f"{DOC_REL_NS}id", "")
                relation = workbook_rels.get(rel_id)
                if relation is None:
                    errors.append(
                        f"workbook pivotCache cacheId={cache_id} 缺少关系 {rel_id!r}"
                    )
                    continue
                rel_type, target = relation
                if rel_type != PIVOT_CACHE_REL:
                    errors.append(
                        f"workbook pivotCache cacheId={cache_id} 的关系类型不是 "
                        "pivotCacheDefinition"
                    )
                    continue
                if target not in names:
                    errors.append(
                        f"workbook pivotCache cacheId={cache_id} 指向不存在的部件: "
                        f"{target}"
                    )
                workbook_caches[cache_id] = target

            pivot_parts = sorted(name for name in names if PIVOT_PART_RE.fullmatch(name))

            # 从 worksheet 关系发现被实际挂载的透视表，避免只凭文件名判断。
            mounted_pivots: set[str] = set()
            for worksheet_part in sorted(
                name
                for name in names
                if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name)
            ):
                worksheet_rels = _relationships(
                    zf,
                    worksheet_part,
                    errors,
                    required=False,
                )
                mounted_pivots.update(
                    target
                    for rel_type, target in worksheet_rels.values()
                    if rel_type == PIVOT_TABLE_REL
                )

            for pivot_part in pivot_parts:
                if pivot_part not in mounted_pivots:
                    errors.append(f"{pivot_part} 未被任何 worksheet 关系引用")

                pivot_root = _read_xml(zf, pivot_part, errors)
                try:
                    pivot_xml = zf.read(pivot_part).decode("utf-8")
                except KeyError:
                    pivot_xml = ""

                pivot_cache_id: int | None = None
                raw_cache_id = pivot_root.get("cacheId", "") if pivot_root is not None else ""
                try:
                    pivot_cache_id = int(raw_cache_id)
                except ValueError:
                    errors.append(f"{pivot_part} cacheId 非法: {raw_cache_id!r}")

                pivot_rels = _relationships(
                    zf,
                    pivot_part,
                    errors,
                    required=True,
                )
                related_cache = _only_relationship_target(
                    pivot_part,
                    pivot_rels,
                    PIVOT_CACHE_REL,
                    errors,
                )
                if related_cache is not None and related_cache not in names:
                    errors.append(f"{pivot_part} 关系指向不存在的部件: {related_cache}")

                workbook_cache = (
                    workbook_caches.get(pivot_cache_id)
                    if pivot_cache_id is not None
                    else None
                )
                if pivot_cache_id is not None and workbook_cache is None:
                    errors.append(
                        f"{pivot_part} 的 cacheId={pivot_cache_id} 未在 workbook 中注册"
                    )
                elif related_cache is not None and workbook_cache != related_cache:
                    errors.append(
                        f"{pivot_part}: cacheId={pivot_cache_id} 对应 workbook 关系 "
                        f"{workbook_cache}，但透视表关系指向 {related_cache}"
                    )

                cache_root = (
                    _read_xml(zf, related_cache, errors)
                    if related_cache is not None and related_cache in names
                    else None
                )
                cache_errors: list[str] = []
                cache_fields, calculated_indices = _validate_cache(
                    cache_root,
                    cache_errors,
                )
                errors.extend(
                    f"{related_cache or pivot_part}: {error}" for error in cache_errors
                )

                pivot_errors: list[str] = []
                _validate_pivot_fields(
                    pivot_root,
                    pivot_xml,
                    cache_fields,
                    calculated_indices,
                    pivot_errors,
                )
                _validate_layout(pivot_root, pivot_xml, pivot_errors)
                errors.extend(f"{pivot_part}: {error}" for error in pivot_errors)

                if related_cache is not None and related_cache in names:
                    cache_rels = _relationships(
                        zf,
                        related_cache,
                        errors,
                        required=True,
                    )
                    records_part = _only_relationship_target(
                        related_cache,
                        cache_rels,
                        PIVOT_RECORDS_REL,
                        errors,
                    )
                    if records_part is not None:
                        if records_part not in names:
                            errors.append(
                                f"{related_cache} 关系指向不存在的部件: {records_part}"
                            )
                        else:
                            _read_xml(zf, records_part, errors)

            orphan_mounted = sorted(mounted_pivots.difference(pivot_parts))
            for pivot_part in orphan_mounted:
                errors.append(f"worksheet 关系指向不存在的透视表部件: {pivot_part}")

            referenced_caches = set(workbook_caches.values())
            actual_caches = {
                name
                for name in names
                if re.fullmatch(
                    r"xl/pivotCache/pivotCacheDefinition\d+\.xml",
                    name,
                )
            }
            for cache_part in sorted(actual_caches.difference(referenced_caches)):
                errors.append(f"{cache_part} 未被 workbook pivotCaches 引用")
    except zipfile.BadZipFile:
        return [f"不是合法 xlsx zip 文件: {path}"]
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
