"""静态 XML 文件模板（workbook / rels / styles / theme / docProps）。

Sheet 名称从 config 读取，不再硬编码。
"""

from pivot_tool.config import PivotConfig
from pivot_tool.xml_utils import XML_HEADER, NS_MAIN, NS_REL, NS_PKG, NS_OREL, rels_xml, xml_escape


def build_static_xml(config: PivotConfig) -> dict[str, str]:
    """返回所有不依赖数据的静态 XML 文件 {路径: 内容}。"""
    O = NS_OREL
    P = NS_PKG

    data_sheet = xml_escape(config.data_sheet_name)
    pivot_sheet = xml_escape(config.pivot_sheet_name)

    return {
        # workbook
        "xl/workbook.xml": (
            f'{XML_HEADER}\n'
            f'<workbook xmlns="{NS_MAIN}" xmlns:r="{NS_REL}">\n'
            f"<sheets>\n"
            f'<sheet name="{pivot_sheet}" sheetId="1" r:id="rId1"/>\n'
            f'<sheet name="{data_sheet}" sheetId="2" r:id="rId2"/>\n'
            f"</sheets>\n"
            f'<pivotCaches><pivotCache cacheId="0" r:id="rId3"/></pivotCaches>\n'
            f"</workbook>"
        ),
        # 全局关系
        "_rels/.rels": rels_xml([
            ("rId1", f"{O}/officeDocument", "xl/workbook.xml"),
            ("rId2", f"{P}/metadata/core-properties", "docProps/core.xml"),
            ("rId3", f"{O}/extended-properties", "docProps/app.xml"),
        ]),
        # workbook 关系
        "xl/_rels/workbook.xml.rels": rels_xml([
            ("rId1", f"{O}/worksheet", "worksheets/sheet1.xml"),
            ("rId2", f"{O}/worksheet", "worksheets/sheet2.xml"),
            ("rId3", f"{O}/pivotCacheDefinition", "pivotCache/pivotCacheDefinition1.xml"),
            ("rId4", f"{O}/theme", "theme/theme1.xml"),
            ("rId5", f"{O}/styles", "styles.xml"),
            ("rId6", f"{O}/sharedStrings", "sharedStrings.xml"),
        ]),
        # sheet1 → pivotTable
        "xl/worksheets/_rels/sheet1.xml.rels": rels_xml([
            ("rId1", f"{O}/pivotTable", "../pivotTables/pivotTable1.xml"),
        ]),
        # pivotCache → records
        "xl/pivotCache/_rels/pivotCacheDefinition1.xml.rels": rels_xml([
            ("rId1", f"{O}/pivotCacheRecords", "pivotCacheRecords1.xml"),
        ]),
        # pivotTable → cache
        "xl/pivotTables/_rels/pivotTable1.xml.rels": rels_xml([
            ("rId1", f"{O}/pivotCacheDefinition", "../pivotCache/pivotCacheDefinition1.xml"),
        ]),
        # 空的 pivot 工作表
        "xl/worksheets/sheet1.xml": (
            f'{XML_HEADER}\n'
            f'<worksheet xmlns="{NS_MAIN}" xmlns:r="{NS_REL}">'
            f"<sheetData/></worksheet>"
        ),
        # Content Types
        "[Content_Types].xml": (
            f'{XML_HEADER}\n'
            f'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
            f'<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
            f'<Default Extension="xml" ContentType="application/xml"/>\n'
            f'<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>\n'
            f'<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>\n'
            f'<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>\n'
            f'<Override PartName="/xl/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>\n'
            f'<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>\n'
            f'<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>\n'
            f'<Override PartName="/xl/pivotCache/pivotCacheDefinition1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.pivotCacheDefinition+xml"/>\n'
            f'<Override PartName="/xl/pivotCache/pivotCacheRecords1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.pivotCacheRecords+xml"/>\n'
            f'<Override PartName="/xl/pivotTables/pivotTable1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.pivotTable+xml"/>\n'
            f'<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>\n'
            f'<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>\n'
            f"</Types>"
        ),
        # styles
        "xl/styles.xml": (
            f'{XML_HEADER}\n'
            f'<styleSheet xmlns="{NS_MAIN}">\n'
            f'<fonts count="1"><font><sz val="11"/><name val="等线"/></font></fonts>\n'
            f'<fills count="2"><fill><patternFill patternType="none"/></fill>'
            f'<fill><patternFill patternType="gray125"/></fill></fills>\n'
            f'<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>\n'
            f'<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>\n'
            f'<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>\n'
            f"</styleSheet>"
        ),
        # theme (最小化)
        "xl/theme/theme1.xml": (
            f'{XML_HEADER}\n'
            f'<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Office Theme">\n'
            f"<a:themeElements>\n"
            f'<a:clrScheme name="Office">\n'
            f'<a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>\n'
            f'<a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>\n'
            f'<a:dk2><a:srgbClr val="44546A"/></a:dk2><a:lt2><a:srgbClr val="E7E6E6"/></a:lt2>\n'
            f'<a:accent1><a:srgbClr val="4472C4"/></a:accent1><a:accent2><a:srgbClr val="ED7D31"/></a:accent2>\n'
            f'<a:accent3><a:srgbClr val="A5A5A5"/></a:accent3><a:accent4><a:srgbClr val="FFC000"/></a:accent4>\n'
            f'<a:accent5><a:srgbClr val="5B9BD5"/></a:accent5><a:accent6><a:srgbClr val="70AD47"/></a:accent6>\n'
            f'<a:hlink><a:srgbClr val="0563C1"/></a:hlink><a:folHlink><a:srgbClr val="954F72"/></a:folHlink>\n'
            f"</a:clrScheme>\n"
            f'<a:fontScheme name="Office">\n'
            f'<a:majorFont><a:latin typeface="Calibri Light"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont>\n'
            f'<a:minorFont><a:latin typeface="Calibri"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont>\n'
            f"</a:fontScheme>\n"
            f'<a:fmtScheme name="Office">\n'
            f"<a:fillStyleLst>"
            f"<a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill>"
            f"<a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill>"
            f"<a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill>"
            f"</a:fillStyleLst>\n"
            f"<a:lnStyleLst>"
            f'<a:ln w="6350"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>'
            f'<a:ln w="6350"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>'
            f'<a:ln w="6350"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>'
            f"</a:lnStyleLst>\n"
            f"<a:effectStyleLst>"
            f"<a:effectStyle><a:effectLst/></a:effectStyle>"
            f"<a:effectStyle><a:effectLst/></a:effectStyle>"
            f"<a:effectStyle><a:effectLst/></a:effectStyle>"
            f"</a:effectStyleLst>\n"
            f"<a:bgFillStyleLst>"
            f"<a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill>"
            f"<a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill>"
            f"<a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill>"
            f"</a:bgFillStyleLst>\n"
            f"</a:fmtScheme>\n"
            f"</a:themeElements>\n"
            f"</a:theme>"
        ),
        # docProps
        "docProps/core.xml": (
            f'{XML_HEADER}\n'
            f'<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"\n'
            f' xmlns:dc="http://purl.org/dc/elements/1.1/">'
            f"<dc:creator>Python Script</dc:creator></cp:coreProperties>"
        ),
        "docProps/app.xml": (
            f'{XML_HEADER}\n'
            f'<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">\n'
            f"<Application>Python</Application></Properties>"
        ),
    }
