"""CLI 入口 (argparse，零外部依赖)。

用法:
  python -m pivot_tool input.csv --preset commercial_ab_test -o output.xlsx
  python -m pivot_tool a.csv b.txt c.xlsx -p commercial_ab_test -o output.xlsx
  python -m pivot_tool *.csv *.txt *.xlsx -c my_config.json -o output.xlsx
  python -m pivot_tool --list-presets
"""

import argparse
import glob
import sys

from pivot_tool.config import load_config, load_preset, validate_config
from pivot_tool.packager import create_xlsx_with_pivot
from pivot_tool.presets import list_presets


def _expand_paths(raw_paths: list[str]) -> list[str]:
    """展开 glob 模式并去重，保持顺序。"""
    result: list[str] = []
    seen: set[str] = set()
    for p in raw_paths:
        expanded = sorted(glob.glob(p)) if ("*" in p or "?" in p) else [p]
        for ep in expanded:
            if ep not in seen:
                seen.add(ep)
                result.append(ep)
    return result


def main():
    parser = argparse.ArgumentParser(
        description="配置驱动的 Excel 原生数据透视表生成工具"
    )
    parser.add_argument(
        "csv_paths", nargs="*", metavar="FILE",
        help="输入 CSV、TXT 或 XLSX 文件路径（支持混合多个文件，自动拼接；支持 glob 模式如 *.csv *.txt *.xlsx）",
    )
    parser.add_argument("--preset", "-p", help="使用内置预设配置")
    parser.add_argument("--config", "-c", dest="config_path", help="使用自定义 JSON 配置文件")
    out_group = parser.add_mutually_exclusive_group()
    out_group.add_argument(
        "--output", "-o", dest="output_path",
        help="完整输出 xlsx 路径（跳过自动命名）。与 -d 互斥；通常不应使用 -e 时同时传 -o",
    )
    out_group.add_argument(
        "--output-dir", "-d", dest="output_dir",
        help="输出目录（文件名仍按 【MMdd-MMdd】实验名.xlsx 自动生成）。与 -o 互斥",
    )
    parser.add_argument("--exp-name", "-e", dest="exp_name", help="实验名称（用于自动命名，如 '广告优化实验'）")
    parser.add_argument(
        "--field-map", "-m", dest="field_map",
        help="字段名映射，格式: 原始名:标准名,原始名2:标准名2（如 total_conv:conv,total_charge:charge）",
    )
    parser.add_argument("--list-presets", action="store_true", help="列出所有可用预设")

    args = parser.parse_args()

    if args.list_presets:
        presets = list_presets()
        if presets:
            print("可用预设:")
            for name in presets:
                print(f"  - {name}")
        else:
            print("没有可用的预设。")
        return

    csv_paths = _expand_paths(args.csv_paths) if args.csv_paths else []
    if not csv_paths:
        print("错误: 请指定至少一个 CSV、TXT 或 XLSX 文件路径。", file=sys.stderr)
        print("用法: python -m pivot_tool a.csv [b.txt b.xlsx ...] --preset <name>", file=sys.stderr)
        sys.exit(1)

    # 加载配置
    if args.config_path:
        config = load_config(args.config_path)
    elif args.preset:
        config = load_preset(args.preset)
    else:
        print("错误: 请指定 --preset 或 --config。", file=sys.stderr)
        sys.exit(1)

    # 校验
    errors = validate_config(config)
    if errors:
        print("配置校验失败:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    # 解析 field_map
    field_map: dict[str, str] | None = None
    if args.field_map:
        try:
            field_map = dict(pair.split(":") for pair in args.field_map.split(","))
        except ValueError:
            print("错误: --field-map 格式错误，应为 原始名:标准名,原始名2:标准名2", file=sys.stderr)
            sys.exit(1)

    # -o + -e 同时给：警告实验名不会拼入文件名
    if args.output_path and args.exp_name:
        print(
            f"警告: --exp-name '{args.exp_name}' 未拼入文件名，因为 -o 已指定完整路径。"
            f"如需自动命名（含日期+实验名），请改用 -d/--output-dir 指定输出目录。",
            file=sys.stderr,
        )

    # 输出路径 (None 时由 packager 从数据自动生成)
    create_xlsx_with_pivot(
        csv_paths, args.output_path, config,
        exp_name=args.exp_name, field_map=field_map, output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
