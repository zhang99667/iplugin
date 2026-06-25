"""组装器：调用所有构建器 → 写 zip (xlsx)。"""

import os
import zipfile
from datetime import date, timedelta

from pivot_tool.config import PivotConfig
from pivot_tool.csv_reader import read_file, read_files, analyze_fields, FieldMaps, align_config_to_headers
from pivot_tool.aliases import auto_apply_aliases
from pivot_tool.xml_utils import clean
from pivot_tool.shared_strings import build_shared_strings
from pivot_tool.data_sheet import build_data_sheet_xml
from pivot_tool.pivot_cache import build_cache_definition, build_cache_records
from pivot_tool.pivot_table import build_pivot_table_xml
from pivot_tool.static_xml import build_static_xml
from pivot_tool.ooxml_guard import assert_valid_pivot_xlsx


def _format_date_segments(days: list[str]) -> str:
    """把 YYYYMMDD 字符串列表按连续区间分段，每段独立包 【】。

    - 单日: 【MMdd】
    - 连续区间: 【MMdd-MMdd】
    - 多段拼接（含跳跃）: 【MMdd】【MMdd-MMdd】
    - 无法解析日期时降级为首尾: 【MMdd-MMdd】
    """
    if not days:
        return ""

    parsed: list[date] = []
    for d in days:
        try:
            parsed.append(date(int(d[:4]), int(d[4:6]), int(d[6:8])))
        except (ValueError, IndexError):
            # 解析失败，降级为首尾
            first, last = days[0][-4:], days[-1][-4:]
            return f"【{first}】" if first == last else f"【{first}-{last}】"

    parsed = sorted(set(parsed))
    segments: list[tuple[date, date]] = []
    seg_start = seg_end = parsed[0]
    for d in parsed[1:]:
        if d == seg_end + timedelta(days=1):
            seg_end = d
        else:
            segments.append((seg_start, seg_end))
            seg_start = seg_end = d
    segments.append((seg_start, seg_end))

    def fmt(d: date) -> str:
        return f"{d.month:02d}{d.day:02d}"

    parts = []
    for s, e in segments:
        parts.append(f"【{fmt(s)}】" if s == e else f"【{fmt(s)}-{fmt(e)}】")
    return "".join(parts)


def _auto_output_name(
    csv_paths: list[str],
    config: PivotConfig,
    headers: list[str],
    rows: list[list[str]],
    exp_name: str | None = None,
    output_dir: str | None = None,
) -> str:
    """从数据和参数自动生成输出文件名。

    优先格式: 【MMdd-MMdd】实验名.xlsx
    日期跳跃时分段: 【MMdd】【MMdd-MMdd】实验名.xlsx
    降级格式: 【MMdd-MMdd】【exp_id值】_pivot.xlsx
    输出目录优先用 output_dir，否则与第一个输入文件相同。
    """
    # 找 event_day 列索引
    date_segment = ""
    try:
        day_idx = config.column_index("event_day")
        days = sorted({clean(r[day_idx]) for r in rows if clean(r[day_idx])})
        date_segment = _format_date_segments(days)
    except ValueError:
        pass

    # 如果有用户指定的实验名，使用新格式
    if exp_name:
        base = f"{date_segment}{exp_name}.xlsx"
    else:
        # 降级：从数据中提取 exp_id
        exp_ids: list[str] = []
        try:
            exp_idx = config.column_index("exp_id")
            seen: set[str] = set()
            for r in rows:
                v = clean(r[exp_idx])
                if v and v not in seen:
                    seen.add(v)
                    exp_ids.append(v)
        except ValueError:
            pass

        parts = [date_segment] if date_segment else []
        if exp_ids:
            parts.append(f"【{'_'.join(exp_ids)}】")

        base = ("".join(parts) if parts else "pivot") + "_pivot.xlsx"

    # 输出目录：优先用显式指定的 output_dir，否则用第一个输入文件所在目录
    out_dir = output_dir or os.path.dirname(csv_paths[0]) or "."
    return os.path.join(out_dir, base)


def avoid_calculated_field_conflicts(headers, config):
    """
    检测并重命名与计算字段同名的源字段，避免生成 xlsx 时字段冲突导致文件损坏。

    将冲突的源字段重命名为 ``{原名}_source``，若仍冲突则追加序号。
    """
    calc_names = {cf.name for cf in config.calculated_fields}
    used = set()
    result = []
    renamed = []

    def next_available(name):
        base = f"{name}_source"
        candidate = base
        index = 2
        while candidate in used or candidate in calc_names:
            candidate = f"{base}_{index}"
            index += 1
        return candidate

    for header in headers:
        new_header = header
        if header in calc_names or header in used:
            new_header = next_available(header)
            renamed.append((header, new_header))
        used.add(new_header)
        result.append(new_header)

    if renamed:
        print(
            "自动重命名与计算字段冲突的源字段: "
            + ", ".join(f"{old}→{new}" for old, new in renamed)
        )

    return result


def create_xlsx_with_pivot(
    csv_paths: str | list[str],
    output_path: str | None,
    config: PivotConfig,
    exp_name: str | None = None,
    field_map: dict[str, str] | None = None,
    output_dir: str | None = None,
) -> str:
    """从 CSV/TXT/XLSX 创建带数据透视表的 Excel 文件。

    csv_paths: 单个路径字符串或路径列表（支持 CSV、TXT 和 XLSX 混合，多文件自动拼接）。
    output_path: 完整输出路径。给定时跳过自动命名。与 output_dir 互斥。
    output_dir: 输出目录。仅指定目录时仍按规则自动生成文件名。
                output_path 与 output_dir 都未给定时，输出到第一个输入文件所在目录。
    exp_name: 实验名称，用于自动命名（如 "广告优化实验"）。
    field_map: 字段名映射，将 CSV 中的别名重命名为标准字段名。
               如 {"total_conv": "conv", "total_charge": "charge"}。
    返回实际输出路径。
    """
    if output_path and output_dir:
        raise ValueError("output_path 与 output_dir 互斥，请只传一个")
    if isinstance(csv_paths, str):
        csv_paths = [csv_paths]

    headers, rows = read_files(csv_paths, xlsx_sheet_name=config.data_sheet_name)

    # 内置别名自动补齐（仅对 headers 缺失的标准名生效，user field_map 永远优先）
    standard_names = [c.name for c in config.columns]
    auto_map = auto_apply_aliases(headers, standard_names, field_map)
    if auto_map:
        print(f"自动应用别名映射: {', '.join(f'{k}→{v}' for k, v in auto_map.items())}")
        field_map = {**auto_map, **(field_map or {})}

    # 字段重命名（别名 → 标准字段名）
    if field_map:
        headers = [field_map.get(h, h) for h in headers]

    # 避免源字段与计算字段重名
    headers = avoid_calculated_field_conflicts(headers, config)

    # 对齐 config.columns 到 CSV headers：预设列保持原定义，多余字段自动推断类型追加
    # 所有字段都进入 pivot cache；多余字段不会被放入行/列/数据/筛选任何区域，
    # 在 Excel 的"数据透视表字段"面板里可手动拖拽
    align_config_to_headers(config, headers, rows)

    # 自动命名
    if not output_path:
        output_path = _auto_output_name(csv_paths, config, headers, rows, exp_name, output_dir=output_dir)

    # 字段分析
    fm = analyze_fields(config, headers, rows)

    # 共享字符串
    ss_xml, ss_map = build_shared_strings(config, headers, rows)

    # 静态 XML
    static = build_static_xml(config)

    # 打包为 xlsx (zip)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in static.items():
            zf.writestr(path, content)
        zf.writestr("xl/sharedStrings.xml", ss_xml)
        zf.writestr(
            "xl/worksheets/sheet2.xml",
            build_data_sheet_xml(config, headers, rows, ss_map),
        )
        zf.writestr(
            "xl/pivotCache/pivotCacheDefinition1.xml",
            build_cache_definition(config, fm),
        )
        zf.writestr(
            "xl/pivotCache/pivotCacheRecords1.xml",
            build_cache_records(config, fm),
        )
        zf.writestr(
            "xl/pivotTables/pivotTable1.xml",
            build_pivot_table_xml(config, fm),
        )

    assert_valid_pivot_xlsx(output_path)

    if len(csv_paths) > 1:
        print(f"已合并 {len(csv_paths)} 个文件")
    print(f"已生成: {output_path}")
    print(f"数据行数: {fm.num_rows}")
    print(f"打开Excel后，数据透视表即可操作（拖拽字段、修改聚合方式等）")
    return output_path
