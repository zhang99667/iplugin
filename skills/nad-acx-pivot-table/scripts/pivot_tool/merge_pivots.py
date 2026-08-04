"""多业务透视表工作簿合并器。

将多个 CSV/TXT 各自生成一个原生透视表，并合并到同一个 xlsx，
业务 sheet 顺序与传入顺序一致，每个业务 2 个 sheet（透视 + 明细）。
"""

import os
import re
import sys
import zipfile

from pivot_tool.config import load_config
from pivot_tool.csv_reader import (
    align_config_to_headers,
    analyze_fields,
    read_file,
)
from pivot_tool.pivot_cache import build_cache_definition, build_cache_records
from pivot_tool.pivot_table import build_pivot_table_xml
from pivot_tool.xml_utils import XML_HEADER, NS_MAIN, NS_REL, col_letter, xml_escape


def _empty_cache_definition(config):
    """生成 0 行数据的合法空 cache 定义。"""
    fields = []
    for col in config.columns:
        fields.append(
            f'<cacheField name="{xml_escape(col.name)}" numFmtId="0">'
            f"<sharedItems count=\"0\"/></cacheField>"
        )
    for cf in config.calculated_fields:
        fields.append(
            f'<cacheField name="{xml_escape(cf.name)}" numFmtId="0" '
            f'formula="{xml_escape(cf.formula)}" databaseField="0"/>'
        )
    return (
        f'{XML_HEADER}\n'
        f'<pivotCacheDefinition xmlns="{NS_MAIN}" xmlns:r="{NS_REL}" '
        f'r:id="rId1" refreshOnLoad="1" createdVersion="8" refreshedVersion="8" '
        f'minRefreshableVersion="3" recordCount="0">'
        f'<cacheSource type="worksheet">'
        f'<worksheetSource ref="A1:{col_letter(len(config.columns) - 1)}1" '
        f'sheet="{xml_escape(config.data_sheet_name)}"/></cacheSource>'
        f'<cacheFields count="{config.total_field_count}">'
        + "".join(fields)
        + "</cacheFields></pivotCacheDefinition>"
    )


def _empty_pivot_table(config, idx):
    """生成 0 行数据的合法空透视表定义。"""
    fields = "".join('<pivotField showAll="0"/>' for _ in range(config.total_field_count))
    data_fields = "".join(
        f'<dataField name="{xml_escape(df.name)}" fld="{config.field_index(df.source_field)}" '
        f'baseField="0" baseItem="0"/>'
        for df in config.pivot_layout.data_fields
    )
    return (
        f'{XML_HEADER}\n'
        f'<pivotTableDefinition xmlns="{NS_MAIN}" '
        f'name="{xml_escape(config.pivot_table_name)}" cacheId="{idx}" '
        f'applyNumberFormats="0" applyBorderFormats="0" applyFontFormats="0" '
        f'applyPatternFormats="0" applyAlignmentFormats="0" applyWidthHeightFormats="1" '
        f'dataCaption="" updatedVersion="8" minRefreshableVersion="3" '
        f'useAutoFormatting="1" itemPrintTitles="1" createdVersion="8" '
        f'indent="0" outline="1" outlineData="1" multipleFieldFilters="0">'
        f'<location ref="A1:B2" firstHeaderRow="1" firstDataRow="2" firstDataCol="1"/>'
        f'<pivotFields count="{config.total_field_count}">{fields}</pivotFields>'
        f'<rowItems count="1"><i t="grand"><x/></i></rowItems>'
        f'<colFields count="1"><field x="-2"/></colFields>'
        f'<colItems count="{len(config.pivot_layout.data_fields) + 1}"><i><x/></i>'
        + "".join(
            f'<i i="{i}"><x v="{i}"/></i>'
            for i in range(1, len(config.pivot_layout.data_fields) + 1)
        )
        + "</colItems>"
        f'<dataFields count="{len(config.pivot_layout.data_fields)}">{data_fields}</dataFields>'
        f'<pivotTableStyleInfo name="{config.pivot_style}" showRowHeaders="1" '
        f'showColHeaders="1" showRowStripes="0" showColStripes="0" showLastColumn="1"/>'
        f"</pivotTableDefinition>"
    )


def _rebuild_data_sheet(config, headers, rows, ss_index):
    """用统一 sharedStrings 重建明细 sheet。"""
    parts = [
        XML_HEADER,
        f'<worksheet xmlns="{NS_MAIN}">',
        f'<dimension ref="A1:{col_letter(len(headers) - 1)}{len(rows) + 1}"/>',
        "<sheetData>",
        '<row r="1">',
    ]
    for ci, h in enumerate(headers):
        parts.append(f'<c r="{col_letter(ci)}1" t="s"><v>{ss_index[h]}</v></c>')
    parts.append("</row>")
    for ri, row in enumerate(rows, 2):
        parts.append(f'<row r="{ri}">')
        for ci, val in enumerate(row):
            cleaned = val.strip().strip('"')
            if not cleaned:
                continue
            ref = f"{col_letter(ci)}{ri}"
            if ci in config.str_col_indices:
                parts.append(f'<c r="{ref}" t="s"><v>{ss_index[cleaned]}</v></c>')
            elif ci in config.int_col_indices:
                try:
                    parts.append(f'<c r="{ref}"><v>{int(float(cleaned))}</v></c>')
                except ValueError:
                    continue
            else:
                try:
                    parts.append(f'<c r="{ref}"><v>{float(cleaned)}</v></c>')
                except ValueError:
                    continue
        parts.append("</row>")
    parts.append("</sheetData></worksheet>")
    return "\n".join(parts)


def create_multi_business_pivot(inputs, output_path):
    """把多个 (CSV, config) 合并为一个多 sheet 透视表工作簿。

    inputs: [(csv_path, config_path), ...]，顺序即 sheet 顺序。
    output_path: 输出 xlsx 完整路径。
    返回实际输出路径。
    """
    if not inputs:
        raise ValueError("至少需要一个输入文件")

    built = []
    for csv_path, cfg_path in inputs:
        config = load_config(cfg_path)
        headers, rows = read_file(csv_path)
        align_config_to_headers(config, headers, rows)
        fm = analyze_fields(config, headers, rows)
        built.append({
            "config": config,
            "headers": headers,
            "rows": rows,
            "fm": fm,
        })

    # 统一 sharedStrings
    strings = []
    index = {}

    def _add(s):
        if s not in index:
            index[s] = len(strings)
            strings.append(s)

    for item in built:
        config = item["config"]
        for h in item["headers"]:
            _add(h)
        for ci in config.str_col_indices:
            for row in item["rows"]:
                v = row[ci].strip().strip('"')
                if v:
                    _add(v)
    ss_xml = (
        f'{XML_HEADER}\n<sst xmlns="{NS_MAIN}" count="{len(strings)}" '
        f'uniqueCount="{len(strings)}">'
        + "".join(f"<si><t>{xml_escape(s)}</t></si>" for s in strings)
        + "</sst>"
    )

    n = len(built)
    sheets_xml = ""
    rel_items = []
    for i, item in enumerate(built):
        pivot_name = item["config"].pivot_sheet_name
        data_name = item["config"].data_sheet_name
        sheets_xml += (
            f'<sheet name="{xml_escape(pivot_name)}" sheetId="{i * 2 + 1}" r:id="rId{i * 2 + 1}"/>'
            f'<sheet name="{xml_escape(data_name)}" sheetId="{i * 2 + 2}" r:id="rId{i * 2 + 2}"/>'
        )
        rel_items += [
            (
                f"rId{i * 2 + 1}",
                "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet",
                f"worksheets/sheet{i * 2 + 1}.xml",
            ),
            (
                f"rId{i * 2 + 2}",
                "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet",
                f"worksheets/sheet{i * 2 + 2}.xml",
            ),
        ]
    # 有数据业务按顺序分配连续 cacheId；空数据业务不注册 pivot cache，
    # 避免 Excel 打开时因空 cache/pivotTable 结构不一致而提示修复
    active_indices = [i for i, item in enumerate(built) if item["rows"]]
    cache_items = ""
    for cache_pos, biz_idx in enumerate(active_indices):
        rid = f"rId{2 * n + 1 + cache_pos}"
        cache_items += f'<pivotCache cacheId="{cache_pos}" r:id="{rid}"/>'
        rel_items.append(
            (
                rid,
                "http://schemas.openxmlformats.org/officeDocument/2006/relationships/pivotCacheDefinition",
                f"pivotCache/pivotCacheDefinition{biz_idx + 1}.xml",
            )
        )
    rel_items += [
        (f"rId{3 * n + 1}", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme", "theme/theme1.xml"),
        (f"rId{3 * n + 2}", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles", "styles.xml"),
        (f"rId{3 * n + 3}", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings", "sharedStrings.xml"),
    ]
    workbook_xml = (
        f'{XML_HEADER}\n<workbook xmlns="{NS_MAIN}" xmlns:r="{NS_REL}">'
        f"<sheets>{sheets_xml}</sheets>"
        f"<pivotCaches>{cache_items}</pivotCaches></workbook>"
    )
    rels_xml = (
        f'{XML_HEADER}\n<Relationships '
        f'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(
            f'<Relationship Id="{rid}" Type="{typ}" Target="{target}"/>'
            for rid, typ, target in rel_items
        )
        + "</Relationships>"
    )

    from pivot_tool.static_xml import build_static_xml
    static = build_static_xml(built[0]["config"])
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in static.items():
            if path.startswith("xl/worksheets/") or path.startswith("xl/pivotCache/") or path.startswith("xl/pivotTables/"):
                continue
            if path in ("xl/workbook.xml", "xl/_rels/workbook.xml.rels", "[Content_Types].xml", "xl/sharedStrings.xml", "_rels/.rels"):
                continue
            zf.writestr(path, content)
        zf.writestr("_rels/.rels", (
            f'{XML_HEADER}\n<Relationships '
            f'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            f'<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            f'<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
            f"</Relationships>"
        ))
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        zf.writestr("[Content_Types].xml", _content_types(n, active_indices))
        zf.writestr("xl/sharedStrings.xml", ss_xml)

        empty_sheet = f'{XML_HEADER}\n<worksheet xmlns="{NS_MAIN}" xmlns:r="{NS_REL}"><sheetData/></worksheet>'
        for i, item in enumerate(built):
            has_data = bool(item["rows"])
            if has_data:
                zf.writestr(f"xl/worksheets/sheet{i * 2 + 1}.xml", empty_sheet)
            else:
                # 空数据业务不生成透视表，只保留一个普通占位 sheet
                zf.writestr(
                    f"xl/worksheets/sheet{i * 2 + 1}.xml",
                    f'{XML_HEADER}\n<worksheet xmlns="{NS_MAIN}" xmlns:r="{NS_REL}">'
                    f'<sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>暂无数据</t></is></c></row></sheetData></worksheet>',
                )
            zf.writestr(
                f"xl/worksheets/sheet{i * 2 + 2}.xml",
                _rebuild_data_sheet(item["config"], item["headers"], item["rows"], index),
            )
            config = item["config"]
            fm = item["fm"]
            if has_data:
                cache_def = build_cache_definition(config, fm)
                cache_records = build_cache_records(config, fm)
                pivot_table = build_pivot_table_xml(config, fm)
                # pivotTable 的 cacheId 必须与 workbook pivotCaches 声明一致；
                # 之前所有业务都写 cacheId=0，Excel 会判定引用冲突并要求恢复
                cache_pos = active_indices.index(i)
                pivot_table = re.sub(
                    r'cacheId="\d+"',
                    f'cacheId="{cache_pos}"',
                    pivot_table,
                    count=1,
                )
                zf.writestr(f"xl/pivotCache/pivotCacheDefinition{i + 1}.xml", cache_def)
                zf.writestr(f"xl/pivotCache/pivotCacheRecords{i + 1}.xml", cache_records)
                zf.writestr(f"xl/pivotTables/pivotTable{i + 1}.xml", pivot_table)
                zf.writestr(
                    f"xl/worksheets/_rels/sheet{i * 2 + 1}.xml.rels",
                    f'{XML_HEADER}\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                    f'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/pivotTable" Target="../pivotTables/pivotTable{i + 1}.xml"/></Relationships>',
                )
                zf.writestr(
                    f"xl/pivotTables/_rels/pivotTable{i + 1}.xml.rels",
                    f'{XML_HEADER}\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                    f'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/pivotCacheDefinition" Target="../pivotCache/pivotCacheDefinition{i + 1}.xml"/></Relationships>',
                )
                zf.writestr(
                    f"xl/pivotCache/_rels/pivotCacheDefinition{i + 1}.xml.rels",
                    f'{XML_HEADER}\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                    f'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/pivotCacheRecords" Target="pivotCacheRecords{i + 1}.xml"/></Relationships>',
                )
    print(f"已生成: {output_path}")
    print(f"业务数: {n}")
    return output_path


def _content_types(n, active_indices):
    items = [
        f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for i in range(1, 2 * n + 1)
    ]
    for i in active_indices:
        i = i + 1
        items += [
            f'<Override PartName="/xl/pivotCache/pivotCacheDefinition{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.pivotCacheDefinition+xml"/>',
            f'<Override PartName="/xl/pivotCache/pivotCacheRecords{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.pivotCacheRecords+xml"/>',
            f'<Override PartName="/xl/pivotTables/pivotTable{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.pivotTable+xml"/>',
        ]
    items += [
        '<Override PartName="/xl/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>',
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
        '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>',
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
    ]
    return (
        f'{XML_HEADER}\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        + "".join(items)
        + "</Types>"
    )


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    pairs = []
    out = None
    i = 0
    while i < len(argv):
        if argv[i] in ("-o", "--output"):
            i += 1
            if i >= len(argv):
                print("缺少 -o 输出路径", file=sys.stderr)
                return 2
            out = argv[i]
        else:
            if i + 1 >= len(argv) or argv[i + 1].startswith("-"):
                print(f"参数 {argv[i]} 需要配对 config 路径", file=sys.stderr)
                return 2
            pairs.append((argv[i], argv[i + 1]))
            i += 1
        i += 1
    if not pairs or not out:
        print("用法: python -m pivot_tool.merge_pivots CSV1 CFG1 CSV2 CFG2 ... -o out.xlsx", file=sys.stderr)
        return 2
    create_multi_business_pivot(pairs, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
