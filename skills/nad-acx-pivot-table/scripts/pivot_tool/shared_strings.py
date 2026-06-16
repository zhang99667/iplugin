"""共享字符串构建器。"""

from pivot_tool.config import PivotConfig
from pivot_tool.xml_utils import XML_HEADER, NS_MAIN, clean, xml_escape


def build_shared_strings(
    config: PivotConfig,
    headers: list[str],
    rows: list[list[str]],
) -> tuple[str, dict[str, int]]:
    """收集所有共享字符串，返回 (xml, {string: index})。

    遍历 config.columns 中 type=="str" 的列，替代硬编码 STR_COLS。
    """
    strings: list[str] = []
    index_map: dict[str, int] = {}

    def _add(s: str) -> None:
        if s not in index_map:
            index_map[s] = len(strings)
            strings.append(s)

    # 表头
    for h in headers:
        _add(h)

    # str 类型列的数据值
    str_indices = config.str_col_indices
    for row in rows:
        for ci in str_indices:
            val = clean(row[ci])
            if val:
                _add(val)

    items = "".join(f"<si><t>{xml_escape(s)}</t></si>" for s in strings)
    xml = (
        f'{XML_HEADER}\n'
        f'<sst xmlns="{NS_MAIN}" count="{len(strings)}" '
        f'uniqueCount="{len(strings)}">{items}</sst>'
    )
    return xml, index_map
