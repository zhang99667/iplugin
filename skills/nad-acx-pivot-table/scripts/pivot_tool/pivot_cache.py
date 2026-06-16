"""数据透视表缓存定义 + 缓存记录构建器。

这是最大重构的模块：通过遍历 config.columns 通用地生成 cacheField，
而非对每列硬编码。
"""

from pivot_tool.config import PivotConfig
from pivot_tool.csv_reader import FieldMaps
from pivot_tool.xml_utils import XML_HEADER, NS_MAIN, NS_REL, clean, xml_escape, col_letter


# ── 缓存定义 ──────────────────────────────────────────────────────


def _build_shared_items_for_col(
    config: PivotConfig, col_idx: int, fm: FieldMaps
) -> str:
    """为单个列生成 <sharedItems> 元素。"""
    col_def = config.columns[col_idx]
    sit = col_def.shared_items_type
    if sit == "auto":
        sit = "enumerated" if col_def.type == "str" else "range"

    has_blank = fm.has_blanks.get(col_idx, False)
    blank_attr = 'containsBlank="1" ' if has_blank else ""

    if sit == "enumerated" and col_def.type == "int":
        # 枚举的整数列 (如 event_day)
        items = fm.enumerated_items[col_idx]
        sorted_items = sorted(items)
        inner = "".join(f'<n v="{v}"/>' for v in sorted_items)
        mn, mx = min(sorted_items), max(sorted_items)
        return (
            f'<sharedItems containsSemiMixedTypes="0" containsString="0" '
            f'{blank_attr}'
            f'containsNumber="1" containsInteger="1" '
            f'minValue="{mn}" maxValue="{mx}" count="{len(items)}">'
            f"{inner}</sharedItems>"
        )

    if sit == "enumerated" and col_def.type == "str":
        # 枚举的字符串列 (如 exp_id)
        items = fm.enumerated_items[col_idx]
        inner = "".join(f'<s v="{xml_escape(v)}"/>' for v in items)
        return f'<sharedItems {blank_attr}count="{len(items)}">{inner}</sharedItems>'

    if sit == "mixed":
        # 混合类型 (如 mt_id: 可能含 "#" 的字符串和纯数字)
        mn, mx = fm.stats.get(col_idx, (0, 0))
        return (
            f'<sharedItems containsMixedTypes="1" containsNumber="1" '
            f'containsInteger="1" minValue="{mn}" maxValue="{mx}"/>'
        )

    if sit == "range":
        # 纯数值范围
        mn, mx = fm.stats.get(col_idx, (0, 0))
        is_int = col_def.type == "int"

        contains_semi = ""
        if not col_def.nullable:
            contains_semi = 'containsSemiMixedTypes="0" '

        contains_str = f'{blank_attr}' if col_def.nullable else ""
        if not col_def.nullable:
            contains_str = 'containsString="0" '
        else:
            contains_str = f'containsString="0" {blank_attr}'

        int_attr = 'containsInteger="1" ' if is_int else ""
        if is_int:
            mn, mx = int(mn), int(mx)
        return (
            f"<sharedItems {contains_semi}{contains_str}"
            f'containsNumber="1" {int_attr}'
            f'minValue="{mn}" maxValue="{mx}"/>'
        )

    # fallback
    return "<sharedItems/>"


def build_cache_definition(
    config: PivotConfig, fm: FieldMaps
) -> str:
    """构建 pivotCacheDefinition XML。"""
    num_rows = fm.num_rows
    last_col = col_letter(fm.num_cols - 1)
    data_range = f"A1:{last_col}{num_rows + 1}"

    cache_fields: list[str] = []
    for i, col_def in enumerate(config.columns):
        si = _build_shared_items_for_col(config, i, fm)
        cache_fields.append(
            f'<cacheField name="{xml_escape(col_def.name)}" numFmtId="0">{si}</cacheField>'
        )

    # 追加计算字段
    for cf in config.calculated_fields:
        cache_fields.append(
            f'<cacheField name="{xml_escape(cf.name)}" numFmtId="0" '
            f'formula="{xml_escape(cf.formula)}" databaseField="0"/>'
        )

    total_count = len(cache_fields)
    fields_xml = "".join(cache_fields)

    return (
        f'{XML_HEADER}\n'
        f'<pivotCacheDefinition xmlns="{NS_MAIN}" xmlns:r="{NS_REL}" r:id="rId1"\n'
        f' refreshOnLoad="1" refreshedBy="Python" refreshedDate="46087.669" createdVersion="8"\n'
        f' refreshedVersion="8" minRefreshableVersion="3" recordCount="{num_rows}">\n'
        f"<cacheSource type=\"worksheet\">\n"
        f'<worksheetSource ref="{data_range}" sheet="{xml_escape(config.data_sheet_name)}"/>\n'
        f"</cacheSource>\n"
        f'<cacheFields count="{total_count}">\n'
        f"{fields_xml}\n"
        f"</cacheFields>\n"
        f"</pivotCacheDefinition>"
    )


# ── 缓存记录 ──────────────────────────────────────────────────────


def build_cache_records(
    config: PivotConfig, fm: FieldMaps
) -> str:
    """构建 pivotCacheRecords XML。

    通用循环：按列类型 + 是否枚举决定输出 <x>/<n>/<s>/<m>。
    """
    rows = fm.rows

    def _encode_cell(col_idx: int, raw_val: str) -> str:
        val = clean(raw_val)
        col_def = config.columns[col_idx]
        sit = col_def.shared_items_type
        if sit == "auto":
            sit = "enumerated" if col_def.type == "str" else "range"

        # 枚举字段优先处理：Strategy Z 下字符串枚举可能把 "" 作为显式项，
        # 这些 cell 必须发出 <x v="idx"/> 而非 <m/>，否则 sharedItems 与
        # records 不一致，Excel 会删除整个 pivotTable。
        if sit == "enumerated" and col_idx in fm.item_index_maps:
            if col_def.type == "int":
                if val == "":
                    return "<m/>"
                sorted_items = sorted(fm.enumerated_items[col_idx])
                return f'<x v="{sorted_items.index(int(val))}"/>'
            m = fm.item_index_maps[col_idx]
            # 字符串枚举按 casefold 查表（与 _unique_ordered 去重规则一致）
            key = val.casefold()
            if key in m:
                return f'<x v="{m[key]}"/>'
            if val == "":
                return "<m/>"
            return f'<s v="{xml_escape(val)}"/>'

        # 空值
        if val == "":
            return "<m/>"

        # mixed 类型 (如 mt_id)
        if sit == "mixed":
            if "#" in val or not val.isdigit():
                return f'<s v="{xml_escape(val)}"/>'
            return f'<n v="{val}"/>'

        # 数值字段 → <n>
        return f'<n v="{val}"/>'

    records_parts: list[str] = []
    for row in rows:
        cells = "".join(
            _encode_cell(ci, row[ci]) for ci in range(len(config.columns))
        )
        records_parts.append(f"<r>{cells}</r>")

    records = "".join(records_parts)
    return (
        f'{XML_HEADER}\n'
        f'<pivotCacheRecords xmlns="{NS_MAIN}" xmlns:r="{NS_REL}" '
        f'count="{fm.num_rows}">{records}</pivotCacheRecords>'
    )
