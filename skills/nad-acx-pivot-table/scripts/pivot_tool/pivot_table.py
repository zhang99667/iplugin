"""数据透视表定义构建器。

从 config.pivot_layout 生成 pivotFields / rowFields / colFields / dataFields。
"""

from pivot_tool.config import PivotConfig, DataFieldDef
from pivot_tool.csv_reader import FieldMaps
from pivot_tool.xml_utils import XML_HEADER, NS_MAIN, xml_escape


def _ordered_enum_values(enum_items: list, configured_order: list | None) -> list:
    """返回完整枚举顺序：配置值优先，未配置值按原始顺序追加。

    ``row_item_order`` 表示优先排序，而不是过滤列表。保留每个枚举值
    恰好一次，既避免重复 ``item``，也确保 sharedItems 中的值不会丢失。
    """
    if not configured_order:
        return list(enum_items)

    def matches(value, configured) -> bool:
        # 字符串枚举与 cache 的大小写不敏感约束保持一致；数值枚举允许
        # JSON 中使用字符串表示，避免排序配置因类型差异静默失效。
        if isinstance(value, str):
            return str(configured).casefold() == value.casefold()
        return configured == value or str(configured) == str(value)

    ordered: list = []
    remaining = list(enum_items)
    for configured in configured_order:
        for value in remaining:
            if matches(value, configured):
                ordered.append(value)
                remaining.remove(value)
                break
    ordered.extend(remaining)
    return ordered


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
            enum_items = fm.enumerated_items[fi]
            field_name = config.all_field_names()[fi]
            configured_order = (
                layout.row_item_order.get(field_name)
                if layout.row_item_order
                else None
            )
            ordered_items = _ordered_enum_values(enum_items, configured_order)
            item_entries = "".join(
                f'<item x="{enum_items.index(value)}"/>' for value in ordered_items
            )

            extra = 1  # default item
            if fm.has_blanks.get(fi, False):
                item_entries += '<item t="blank"/>'
                extra += 1
            item_entries += '<item t="default"/>'
            # count 以实际生成的 item 子节点为准，防止配置只列部分枚举值时
            # 声明数量与 XML 内容不一致，导致旧版 Excel 加载时崩溃。
            item_count = len(ordered_items) + extra
            items_xml = f'<items count="{item_count}">{item_entries}</items>'
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
    row_item_count = 0
    if row_indices:
        # 计算行项数量：枚举值数 + grand total
        first_row_field = row_indices[0]
        if first_row_field in fm.enumerated_items:
            field_name = config.all_field_names()[first_row_field]
            configured_order = (
                layout.row_item_order.get(field_name)
                if layout.row_item_order
                else None
            )
            first_items = _ordered_enum_values(
                fm.enumerated_items[first_row_field], configured_order
            )
        else:
            first_items = []

        if len(row_indices) > 1 and first_items:
            # 多级行字段：每个第一层值下展开第二层值
            second_row_field = row_indices[1]
            second_items = (
                list(fm.enumerated_items.get(second_row_field, []))
                if second_row_field in fm.enumerated_items
                else []
            )
            items = []
            for first_idx in range(len(first_items)):
                # 第一层组头行
                items.append(
                    "<i><x/></i>" if first_idx == 0 else f'<i><x v="{first_idx}"/></i>'
                )
                # 第二层子行
                for second_idx in range(len(second_items)):
                    if second_idx == 0:
                        items.append('<i r="1"><x/></i>')
                    else:
                        items.append(f'<i r="1"><x v="{second_idx}"/></i>')
            items.append('<i t="grand"><x/></i>')
            row_item_count = len(items)
            row_items_xml = (
                f'<rowItems count="{row_item_count}">{"".join(items)}</rowItems>'
            )
        else:
            num_row_items = len(first_items) if first_items else 2
            items = []
            for i in range(num_row_items):
                if i == 0:
                    items.append("<i><x/></i>")
                else:
                    items.append(f'<i><x v="{i}"/></i>')
            items.append('<i t="grand"><x/></i>')
            row_item_count = len(items)
            row_items_xml = f'<rowItems count="{row_item_count}">{"".join(items)}</rowItems>'

    # ── pageFields (筛选字段) ─────────────────────────────────────
    page_fields_xml = ""
    if filter_indices:
        inner = "".join(f'<pageField fld="{i}" hier="-1"/>' for i in filter_indices)
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
    # 估算枚举行项数；最终范围还会额外包含 grand total。
    if row_item_count:
        num_data_rows = row_item_count - 1
    else:
        num_data_rows = 2

    last_data_col = col_letter_for_count(num_data_fields + 1)

    # location 只描述透视主体，不包含 pageFields。页面筛选字段纵向占 N 行，
    # 与主体之间还要留 1 个空行；否则从 A1 开始的主体会与筛选区重叠，
    # Excel 会在打开时提示修复。有页面筛选时 firstDataRow=1 已由 Excel
    # 与 LibreOffice 对同一布局的重写结果共同验证；无筛选时保留既有的
    # Values 标签行规则，避免改变已经生成的普通透视布局。
    page_field_count = len(filter_indices)
    first_body_row = page_field_count + 2 if page_field_count else 1
    num_header_rows = 1 if page_field_count else (2 if col_fields_xml else 1)
    last_body_row = first_body_row + num_header_rows + num_data_rows
    location_ref = f"A{first_body_row}:{last_data_col}{last_body_row}"
    location_attrs = [
        f'ref="{location_ref}"',
        'firstHeaderRow="0"',
        f'firstDataRow="{num_header_rows}"',
        'firstDataCol="1"',
    ]
    if page_field_count:
        location_attrs.extend(
            [f'rowPageCount="{page_field_count}"', 'colPageCount="1"']
        )

    return (
        f'{XML_HEADER}\n'
        f'<pivotTableDefinition xmlns="{NS_MAIN}" '
        f'name="{xml_escape(config.pivot_table_name)}" cacheId="0"\n'
        f' applyNumberFormats="0" applyBorderFormats="0" applyFontFormats="0"\n'
        f' applyPatternFormats="0" applyAlignmentFormats="0" applyWidthHeightFormats="1"\n'
        f' dataCaption="" updatedVersion="8" minRefreshableVersion="3"\n'
        f' useAutoFormatting="1" itemPrintTitles="1" createdVersion="8"\n'
        f' indent="0" outline="1" outlineData="1" multipleFieldFilters="0">\n'
        f'<location {" ".join(location_attrs)}/>\n'
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
