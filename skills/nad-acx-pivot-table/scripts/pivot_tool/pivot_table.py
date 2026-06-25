"""数据透视表定义构建器。

从 config.pivot_layout 生成 pivotFields / rowFields / colFields / dataFields。
"""

from pivot_tool.config import PivotConfig, DataFieldDef
from pivot_tool.csv_reader import FieldMaps
from pivot_tool.xml_utils import XML_HEADER, NS_MAIN, xml_escape


def build_pivot_table_xml(config: PivotConfig, fm: FieldMaps) -> str:
    """构建 pivotTableDefinition XML。"""
    layout = config.pivot_layout
    total_fields = config.total_field_count
    num_data_fields = len(layout.data_fields)

    # ── 收集 axis 信息 ───────────────────────────────────────────
    row_indices = [config.field_index(f) for f in layout.row_fields]
    col_indices = [config.field_index(f) for f in layout.col_fields if f != "__data__"]
    filter_indices = [config.field_index(f) for f in layout.filter_fields]

    # data_fields 使用的 source 字段索引集合
    data_source_indices: set[int] = set()
    for df in layout.data_fields:
        data_source_indices.add(config.field_index(df.source_field))

    # 计算字段索引集合
    calc_start = len(config.columns)
    calc_indices = set(range(calc_start, total_fields))

    # ── pivotFields ──────────────────────────────────────────────
    pivot_fields: list[str] = []
    for fi in range(total_fields):
        attrs: list[str] = []

        if fi in row_indices:
            attrs.append('axis="axisRow"')
        elif fi in col_indices:
            attrs.append('axis="axisCol"')
        elif fi in filter_indices:
            attrs.append('axis="axisPage"')

        if fi in data_source_indices:
            attrs.append('dataField="1"')

        # 计算字段特殊属性
        if fi in calc_indices:
            attrs.append('dragToRow="0" dragToCol="0" dragToPage="0"')

        attrs.append('showAll="0"')

        if fi in calc_indices:
            attrs.append('defaultSubtotal="0"')
        attr_str = " ".join(attrs)

        # 生成 items：对所有枚举字段都生成（无论是否在 axis 上）。
        # 当 sharedItems 声明 containsBlank="1" 时，items 必须追加 <item t="blank"/>，
        # 否则 items 与 sharedItems 的声明不一致，Excel 会删除整个 pivotTable 部件。
        if fi in fm.enumerated_items:
            num_items = len(fm.enumerated_items[fi])

            field_name = config.all_field_names()[fi]
            if layout.row_item_order and field_name in layout.row_item_order:
                order = layout.row_item_order[field_name]
                enum_items = fm.enumerated_items[fi]
                item_entries = "".join(
                    f'<item x="{enum_items.index(v)}"/>' for v in order if v in enum_items
                )
            else:
                item_entries = "".join(f'<item x="{i}"/>' for i in range(num_items))

            extra = 1  # default item
            if fm.has_blanks.get(fi, False):
                item_entries += '<item t="blank"/>'
                extra += 1
            item_entries += '<item t="default"/>'
            items_xml = f'<items count="{num_items + extra}">{item_entries}</items>'
            pivot_fields.append(f"<pivotField {attr_str}>{items_xml}</pivotField>")
        else:
            pivot_fields.append(f"<pivotField {attr_str}/>")

    pivot_fields_xml = "".join(pivot_fields)

    # ── rowFields ────────────────────────────────────────────────
    row_fields_xml = ""
    if row_indices:
        inner = "".join(f'<field x="{i}"/>' for i in row_indices)
        row_fields_xml = f'<rowFields count="{len(row_indices)}">{inner}</rowFields>'

    # ── rowItems ─────────────────────────────────────────────────
    row_items_xml = ""
    if row_indices:
        # 计算行项数量：枚举值数 + grand total
        first_row_field = row_indices[0]
        if first_row_field in fm.enumerated_items:
            field_name = config.all_field_names()[first_row_field]
            if layout.row_item_order and field_name in layout.row_item_order:
                num_row_items = len(layout.row_item_order[field_name])
            else:
                num_row_items = len(fm.enumerated_items[first_row_field])
        else:
            num_row_items = 2  # fallback

        items = []
        for i in range(num_row_items):
            if i == 0:
                items.append("<i><x/></i>")
            else:
                items.append(f'<i><x v="{i}"/></i>')
        items.append('<i t="grand"><x/></i>')
        row_items_xml = f'<rowItems count="{num_row_items + 1}">{"".join(items)}</rowItems>'

    # ── pageFields (筛选字段) ─────────────────────────────────────
    page_fields_xml = ""
    if filter_indices:
        inner = "".join(f'<pageField fld="{i}"/>' for i in filter_indices)
        page_fields_xml = f'<pageFields count="{len(filter_indices)}">{inner}</pageFields>'

    # ── colFields ────────────────────────────────────────────────
    col_fields_xml = ""
    col_items_xml = ""
    has_data_col = "__data__" in layout.col_fields

    if has_data_col or col_indices:
        entries: list[str] = []
        if has_data_col:
            entries.append('<field x="-2"/>')
        for ci in col_indices:
            entries.append(f'<field x="{ci}"/>')
        col_fields_xml = (
            f'<colFields count="{len(entries)}">{"".join(entries)}</colFields>'
        )

    if has_data_col:
        col_item_entries = ["<i><x/></i>"]
        for i in range(1, num_data_fields):
            col_item_entries.append(f'<i i="{i}"><x v="{i}"/></i>')
        col_items_xml = (
            f'<colItems count="{num_data_fields}">'
            f'{"".join(col_item_entries)}</colItems>'
        )

    # ── dataFields ───────────────────────────────────────────────
    data_fields_parts: list[str] = []
    for df in layout.data_fields:
        fld_idx = config.field_index(df.source_field)
        attrs = f'name="{xml_escape(df.name)}" fld="{fld_idx}"'

        if df.show_data_as == "percentDiff":
            base_fld = config.field_index(df.base_field) if df.base_field else 0
            attrs += (
                f' showDataAs="percentDiff" baseField="{base_fld}" '
                f'baseItem="{df.base_item}" numFmtId="{df.num_fmt_id}"'
            )
        else:
            attrs += f' baseField="0" baseItem="0"'
            if df.num_fmt_id:
                attrs += f' numFmtId="{df.num_fmt_id}"'

        data_fields_parts.append(f"<dataField {attrs}/>")

    data_fields_xml = (
        f'<dataFields count="{num_data_fields}">'
        f'{"".join(data_fields_parts)}</dataFields>'
    )

    # ── location ─────────────────────────────────────────────────
    # 估算行数
    if row_indices and row_indices[0] in fm.enumerated_items:
        field_name = config.all_field_names()[row_indices[0]]
        if layout.row_item_order and field_name in layout.row_item_order:
            num_data_rows = len(layout.row_item_order[field_name])
        else:
            num_data_rows = len(fm.enumerated_items[row_indices[0]])
    else:
        num_data_rows = 2

    last_data_col = col_letter_for_count(num_data_fields + 1)
    # colFields 含 __data__ 时 Excel 渲染 2 行表头 (Values 标签行 + 字段名行)
    has_explicit_col_fields = bool(col_fields_xml)
    num_header_rows = 2 if has_explicit_col_fields else 1
    last_row = num_header_rows + num_data_rows + 1
    location_ref = f"A1:{last_data_col}{last_row}"
    first_data_row = num_header_rows

    return (
        f'{XML_HEADER}\n'
        f'<pivotTableDefinition xmlns="{NS_MAIN}" '
        f'name="{xml_escape(config.pivot_table_name)}" cacheId="0"\n'
        f' applyNumberFormats="0" applyBorderFormats="0" applyFontFormats="0"\n'
        f' applyPatternFormats="0" applyAlignmentFormats="0" applyWidthHeightFormats="1"\n'
        f' dataCaption="" updatedVersion="8" minRefreshableVersion="3"\n'
        f' useAutoFormatting="1" itemPrintTitles="1" createdVersion="8"\n'
        f' indent="0" outline="1" outlineData="1" multipleFieldFilters="0">\n'
        f'<location ref="{location_ref}" firstHeaderRow="0" firstDataRow="{first_data_row}" firstDataCol="1"/>\n'
        f'<pivotFields count="{total_fields}">{pivot_fields_xml}</pivotFields>\n'
        f'{row_fields_xml}\n'
        f'{row_items_xml}\n'
        f'{col_fields_xml}\n'
        f'{col_items_xml}\n'
        f'{page_fields_xml}\n'
        f'{data_fields_xml}\n'
        f'<pivotTableStyleInfo name="{config.pivot_style}" showRowHeaders="1" showColHeaders="1"\n'
        f' showRowStripes="0" showColStripes="0" showLastColumn="1"/>\n'
        f'</pivotTableDefinition>'
    )


def col_letter_for_count(n: int) -> str:
    """将列数转换为 Excel 列字母（1→A, 14→N）。"""
    from pivot_tool.xml_utils import col_letter
    return col_letter(n - 1)
