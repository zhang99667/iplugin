"""数据工作表构建器。"""

from pivot_tool.config import PivotConfig
from pivot_tool.xml_utils import XML_HEADER, NS_MAIN, NS_REL, clean, col_letter


def build_data_sheet_xml(
    config: PivotConfig,
    headers: list[str],
    rows: list[list[str]],
    ss_map: dict[str, int],
) -> str:
    """生成数据工作表 XML。

    按 column.type 决定单元格格式，替代硬编码 STR_COLS/INT_COLS。
    """
    num_cols = len(headers)
    last_col = col_letter(num_cols - 1)
    str_indices = config.str_col_indices
    int_indices = config.int_col_indices

    parts = [
        XML_HEADER,
        f'<worksheet xmlns="{NS_MAIN}" xmlns:r="{NS_REL}">',
        f'<dimension ref="A1:{last_col}{len(rows) + 1}"/>',
        "<sheetData>",
        '<row r="1">',
    ]

    # 表头行
    for ci, h in enumerate(headers):
        ref = f"{col_letter(ci)}1"
        parts.append(f'<c r="{ref}" t="s"><v>{ss_map[h]}</v></c>')
    parts.append("</row>")

    # 数据行
    for ri, row in enumerate(rows, 2):
        parts.append(f'<row r="{ri}">')
        for ci, val in enumerate(row):
            cleaned = clean(val)
            if not cleaned:
                continue
            ref = f"{col_letter(ci)}{ri}"
            if ci in str_indices:
                parts.append(f'<c r="{ref}" t="s"><v>{ss_map[cleaned]}</v></c>')
            elif ci in int_indices:
                try:
                    parts.append(f'<c r="{ref}"><v>{int(float(cleaned))}</v></c>')
                except (ValueError, TypeError):
                    pass  # 跳过无法转换为数值的占位符（如 '-'）
            else:
                try:
                    parts.append(f'<c r="{ref}"><v>{float(cleaned)}</v></c>')
                except (ValueError, TypeError):
                    pass  # 跳过无法转换为数值的占位符
        parts.append("</row>")

    parts.append("</sheetData></worksheet>")
    return "\n".join(parts)
