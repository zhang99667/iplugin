"""XML 工具函数和命名空间常量。"""

# ── XML 命名空间常量 ──────────────────────────────────────────────
NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
NS_OREL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

XML_HEADER = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'


def clean(val: str) -> str:
    """清除 CSV 值的首尾空白和引号。"""
    return val.strip().strip('"')


def col_letter(col_idx: int) -> str:
    """将 0-based 列索引转换为 Excel 列字母 (0→A, 25→Z, 26→AA)。"""
    result = ""
    idx = col_idx
    while True:
        result = chr(ord("A") + idx % 26) + result
        idx = idx // 26 - 1
        if idx < 0:
            break
    return result


def xml_escape(s: str) -> str:
    """XML 特殊字符转义。"""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def rels_xml(relationships: list[tuple[str, str, str]]) -> str:
    """生成 .rels 关系文件 XML。

    relationships: [(id, type_url, target), ...]
    """
    items = "".join(
        f'<Relationship Id="{rid}" Type="{rtype}" Target="{target}"/>'
        for rid, rtype, target in relationships
    )
    return f'{XML_HEADER}\n<Relationships xmlns="{NS_PKG}">{items}</Relationships>'
