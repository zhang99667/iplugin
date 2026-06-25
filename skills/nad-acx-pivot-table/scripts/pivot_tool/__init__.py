"""pivot_tool — 配置驱动的 Excel 原生数据透视表生成工具。

通过手拼 OOXML XML 生成 Excel 原生可操作数据透视表。
支持预设配置和自定义 JSON 配置文件。
"""

def create_xlsx_with_pivot(*args, **kwargs):
    from pivot_tool.packager import create_xlsx_with_pivot as _create_xlsx_with_pivot

    return _create_xlsx_with_pivot(*args, **kwargs)

__all__ = ["create_xlsx_with_pivot"]
