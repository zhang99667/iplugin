---
name: nad-acx-pivot-table
version: 0.1.6
description: 专用于生成商业 AB 实验数据分析透视表 xlsx 文件（通过手拼 OOXML XML，绕过 openpyxl 不支持创建透视表的限制）。支持单个 CSV/TXT/XLSX 文件自动生成，以及多个 CSV/TXT/XLSX 文件合并生成（如多天数据合并）。TXT 必须是带表头的分隔符文本（支持逗号、Tab、分号、竖线分隔）。输入文件必须包含以下标准字段：exp_id、event_day、eshow、click、charge、tcharge、conv；部分常见别名（如 total_target_charge → tcharge、total_conv → conv、eshows → eshow 等）会被内置别名表自动映射，未登记的别名可通过 --field-map 手动指定，或由 Step 4b 子串建议自动探测，详见 SKILL.md Step 4。TRIGGER when：用户说"透视表"、"pivot table"、"数据透视"、"AB 测试报表"、"生成 xlsx 透视表"、"合并 csv/txt 生成分析"、"商业 AB 实验数据透视表"、"给这个文件生成透视表"、"合并 Downloads 前 N 个 csv/txt 生成透视表"、"合并最近 N 个 csv/txt 生成透视表"、"用 xxx.csv/xxx.txt 生成透视表"、"合并这 N 个 csv/txt 文件生成透视表，实验名是 xxx"（用户在同一句话里同时给出文件范围 + 实验名，应跳过所有 AskUserQuestion 直接生成），或任何提到"生成/合并"+"透视表/数据透视/AB 实验报表"的自然语言描述（无论是否显式说"商业"或文件路径）。DO NOT TRIGGER when：用户只需读取/展示数据内容、或生成普通格式 xlsx（无透视功能）、或字段语义完全不属于商业 AB 实验数据。
tags: [excel, pivot-table, xlsx, commercial-ads, ab-test, nad, acx]
autoInstall: true
autoUpdate: true
localDebug: false
---

# Pivot Table

## Overview

专用于**商业 AB 实验数据**的 Excel 原生数据透视表生成工具。通过手拼 OOXML XML 绕过 openpyxl 不支持创建透视表的限制，生成的透视表在 Excel 中可拖拽字段、刷新数据、修改聚合方式。

**输入文件必需字段**（标准字段名；部分常见别名会自动映射，详见 [Step 4](#step-4-校验必需字段)）：

| 字段 | 说明 |
|------|------|
| `exp_id` | 实验对照组 ID（如 `dz`=对照组，`exp`=实验组） |
| `event_day` | 日期（用于输出文件命名，格式如 `20240419`） |
| `eshow` | 广告曝光数量 |
| `click` | 广告点击数量 |
| `charge` | 广告消费 |
| `tcharge` | 广告预计收费 |
| `conv` | 广告转化数量 |

> **别名处理**：CSV 中出现的常见别名（如 `exp`/`eid` → `exp_id`、`total_target_charge` → `tcharge`、`total_conv`/`cv`/`total_convert_num` → `conv`、`eshows` → `eshow`、`clicks` → `click`）会被 `pivot_tool/aliases.py` 的 `FIELD_ALIASES` 在运行时自动映射，无需手动操作；未登记的别名可通过 `--field-map` 手动指定，或由 Step 4b 子串建议引导。完整别名表见 Step 4a。

支持两种使用模式：
1. **预设模式** — 使用内置配置（如 `commercial_ab_test`）一键生成
2. **自定义配置模式** — 用户编写 JSON 配置文件定义列、计算字段和透视布局

## 透视表输出格式

### 自动计算字段

工具基于原始字段自动派生 3 个计算字段：

| 计算字段 | 公式 | 说明 |
|----------|------|------|
| `ectr` | `click / eshow` | 点击率（广告点击数 / 曝光数） |
| `cvr` | `conv / click` | 转化率（转化数 / 点击数） |
| `evr` | `conv / eshow` | 展现转化率（转化数 / 曝光数） |

### 透视表布局

生成的透视表布局如下：

- **行**：`exp_id`（实验组，每行对应一个实验/对照组，通常为 `dz` 和 `exp`）
- **列**：数据字段横向展开（含 Values 标签行）
- **数据列**：共 13 列，按原始指标绝对值 + 相对基准差异交替排列

```
            | 求和项:eshow | eshow相对差 | 求和项:click | click相对差 | 求和项:charge | charge相对差 | 求和项:tcharge | tcharge相对差 | 求和项:conv | conv相对差 | ectr相对差 | cvr相对差 | evr相对差 |
---------   |-------------|------------|-------------|------------|--------------|-------------|---------------|--------------|------------|-----------|-----------|----------|----------|
dz（对照）  |   1,200,000 |          — |      36,000 |          — |      120,000 |           — |       130,000 |            — |        900 |         — |        — |        — |        — |
exp（实验） |   1,230,000 |      +2.5% |      38,000 |      +5.6% |      124,800 |        +4.0% |       134,000 |         +3.1% |        990 |     +10.0% |    +3.0% |    +4.2% |    +7.3% |
总计        |   2,430,000 |            |      74,000 |            |      244,800 |             |       264,000 |              |      1,890 |           |          |          |          |
```

> 相对差列（`percentDiff`）以 `dz`（对照组，第一个枚举值）为基准，计算实验组相对对照组的百分比变化。

### 输出文件结构

生成的 xlsx 包含两个 sheet（sheet 名由配置决定，下表为预设 `commercial_ab_test` 的实际值）：

| Sheet | 内容 |
|-------|------|
| 实验组数据透视 | Excel 原生透视表（可拖拽字段、刷新、修改聚合方式）。透视表对象名为 `数据透视表`（`pivot_table_name`） |
| 原始数据 | 合并后的原始 CSV 数据（用于透视表数据源和历史数据追加） |

## Quick Start

> **输出路径约定（重要）**：
> - **默认（推荐）**：不传 `-o`/`-d`，工具按 `【MMdd-MMdd】实验名.xlsx` 自动命名，输出到第一个输入文件所在目录。例如 `-e "健康竞胜率"` 生成 `【0621-0624】健康竞胜率.xlsx`。
> - **`-d/--output-dir <目录>`**：仅自定义输出**目录**，文件名仍按规则自动生成。**外部 agent / 自动化脚本想指定输出位置时应使用 `-d`，而不是 `-o`。**
> - **`-o/--output <完整路径>`**：完整跳过自动命名，直接用给定路径。一旦传 `-o`，`-e` 实验名将不会拼入文件名（工具会在 stderr 输出警告）。
> - `-o` 与 `-d` 互斥。

```bash
# 所有命令均在 skill scripts 目录下运行（与项目目录无关）
SCRIPTS=<本 skill 目录>/scripts

# 单文件 + 预设 + 实验名（自动命名: 【0419-0422】流量优化.xlsx）
cd "$SCRIPTS" && python3 -m pivot_tool input.txt -p commercial_ab_test -e "流量优化"

# 自定义输出目录 + 自动命名（推荐用于外部 agent 调用）
cd "$SCRIPTS" && python3 -m pivot_tool input.csv -p commercial_ab_test -e "流量优化" -d /tmp/output

# 追加新数据：已有透视表 xlsx + 新 CSV/TXT，重新生成（读取 xlsx 的"原始数据" sheet）
cd "$SCRIPTS" && python3 -m pivot_tool old_pivot.xlsx new_data.txt -p commercial_ab_test -e "流量优化"

# 多文件合并（CSV + TXT + XLSX 混合）
cd "$SCRIPTS" && python3 -m pivot_tool a.csv b.txt c.xlsx -p commercial_ab_test -e "广告策略AB"

# glob 模式
cd "$SCRIPTS" && python3 -m pivot_tool /path/to/*.csv /path/to/*.txt -c my_config.json -e "实验名"

# 完整自定义路径（仅在确实需要固定文件名时使用；-e 实验名不会拼入文件名）
cd "$SCRIPTS" && python3 -m pivot_tool input.csv --config my_config.json -o output.xlsx

# 列出可用预设
cd "$SCRIPTS" && python3 -m pivot_tool --list-presets
```

生成命令会自动运行 `pivot_tool.ooxml_guard` 做 PivotTable OOXML 兼容性闸门校验。该闸门会拦截 zip/openpyxl 可能放过、但 Excel 打开时会提示修复的问题；如需单独诊断已生成文件，可运行：

```bash
cd "$SCRIPTS" && python3 -m pivot_tool.ooxml_guard output.xlsx
```

## 用户配置持久化

### 配置文件

路径：`~/.config/iplugin/nad-acx-pivot-table/user_config.json`

```json
{
  "default_dir": "~/Downloads",
  "field_map": ""
}
```

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `default_dir` | 默认 CSV/TXT/XLSX 目录，Step 1 直接使用，跳过询问 | 无（首次必问） |
| `field_map` | 默认字段映射（空字符串 = 无映射），Step 3.5 直接使用，跳过询问 | 无（首次必问） |

### 读取配置

每次流程开始时，先用 Python 读取配置文件：

```python
import json, os
config_path = os.path.expanduser('~/.config/iplugin/nad-acx-pivot-table/user_config.json')
try:
    with open(config_path) as f:
        user_cfg = json.load(f)
except FileNotFoundError:
    user_cfg = {}
```

- `user_cfg` 为空 dict 表示首次运行，需完整引导
- `user_cfg` 有值则跳过对应步骤，直接使用已保存的值

### 保存配置

Step 6 生成成功后，将本次使用的 `default_dir` 和 `field_map` 写回配置文件：

```python
os.makedirs(os.path.dirname(config_path), exist_ok=True)
with open(config_path, 'w') as f:
    json.dump({"default_dir": used_dir, "field_map": used_field_map}, f, ensure_ascii=False, indent=2)
```

### 修改配置（主动触发）

**触发词**：用户说"修改配置"、"重置配置"、"更改设置"、"配置目录"、"配置字段映射"时，进入配置编辑流程：

1. 读取当前配置文件，展示当前值
2. 用 AskUserQuestion 让用户选择要修改哪项（目录 / 字段映射 / 全部重置）
3. 收集新值后写回配置文件
4. 告知用户"配置已更新，下次生成透视表时自动生效"

---

## 引导式工作流（核心流程）

当用户要求生成透视表时，按以下步骤逐一引导。

> **CRITICAL — AskUserQuestion 全局约束**：本流程所有 AskUserQuestion 调用，用户可见文案必须全部使用中文，包括 `header`、`question`、`label`、`description`，禁止出现 `Which files should be used?`、`How should the experiment name be set?`、`File 1`、`Custom` 等英文引导或英文选项。参数中的**非 ASCII 字符（包括中文）必须用 Unicode 转义**（如 `文件` → `\u6587\u4ef6`）。否则底层 JSON 解析器会将整个 `questions` 参数误识别为 `string` 而非 `array`，报 `InputValidationError: type is expected as array but provided as string`，用户将看不到任何选项。

### Step 0: 读取用户配置

流程开始时先读取 `~/.config/iplugin/nad-acx-pivot-table/user_config.json`，后续步骤按配置跳过或执行。

> 若用户本轮请求是"修改配置 / 重置配置 / 配置目录 / 配置字段映射"等语义，跳到上文 [修改配置（主动触发）](#修改配置主动触发)，不要走下面的生成流程。

### Step 1: 确认数据文件路径

- **有 `default_dir` 配置**：直接使用，告知用户「使用默认目录 `<dir>`，如需修改请说"修改配置"」，跳过询问
- **无配置（首次）**：用 AskUserQuestion 询问目录路径，提供常用选项

### Step 2: 列出文件并选择

#### 2.0 用户已显式指定文件时跳过询问（快速通道）

如果用户的请求里**已经明确指定了文件范围**，**跳过列表展示和 AskUserQuestion**，直接组装文件列表进 Step 3。识别规则：

| 用户表述模式 | 处理方式 |
|---|---|
| "前 N 个 csv/txt"、"最近 N 个 csv/txt"、"top N csv/txt" | 列文件按 birthtime 倒序，取前 N 个 CSV/TXT（跳过 xlsx）|
| "这 N 个 csv/txt"、"这三个 txt 文件"、"这几个数据文件" | 同上，按 birthtime 倒序取前 N 个 CSV/TXT（默认目录） |
| "这个文件 xxx.csv/xxx.txt"、"用 xxx.txt 生成"、显式给出文件名/路径 | 直接用指定文件，校验存在即可 |
| "Downloads 里 0505 的 csv/txt"、"包含 xxx 的文件" | 列文件后按文件名片段过滤 |
| 没有任何文件线索 | 走下面 2.1 / 2.2 的常规询问流程 |

**实验名内联识别**（同样跳过 AskUserQuestion）：

| 用户表述 | 解析后实验名 |
|---|---|
| "实验名是【XXX】" / "实验名为 XXX" / "实验名叫 XXX" | `XXX`（去掉【】等装饰符号） |
| "命名为 XXX" / "起名 XXX" | `XXX` |
| "实验名是 XXX，YYY" 等含逗号 | 完整 `XXX，YYY` 当一个实验名 |
| 用户没提实验名 | 走自动命名（exp_id + 日期） |

**联动规则**：当用户**同一句话同时给出文件范围 + 实验名**（如「合并下这三个 csv/txt 文件，并生成透视表，实验名是【直播按钮延迟展现】」），**完全跳过 AskUserQuestion**，整个流程从 Step 2.0 直接跳到 Step 3。

快速通道仍需向用户**回显选中的文件清单 + 实验名**（一行简短列表），便于确认无误，但不需要再用 AskUserQuestion 收集。

示例 1（文件范围 + 实验名一句话给齐）：
```
用户："合并下这三个 csv/txt 文件，并生成透视表，实验名是【直播按钮延迟展现】"
助手回显：「使用 ~/Downloads 中最新创建的 3 个 CSV/TXT：
  1. 任务ID_84657194.txt
  2. 任务ID_84657172.csv
  3. 任务ID_84656923.txt
实验名：直播按钮延迟展现」→ 直接进入 Step 3，全程零 AskUserQuestion
```

示例 2（只给文件不给实验名）：
```
用户："合并 Downloads 前 3 个 csv/txt 生成透视表"
助手识别文件范围为前 3 个 CSV/TXT，但实验名缺失 → 不需要再开 AskUserQuestion，直接走自动命名（不再追问，"实验名"非必需）
```

#### 2.1 常规询问流程

使用 Python 获取全部文件列表（含大小，**按创建时间 `st_birthtime` 倒序**——比 mtime 稳定，不会因 Spotlight/iCloud/QuickLook 等无意触动而变化）后，**直接在回复文本中输出编号列表**，然后用 **1 次 AskUserQuestion** 收集文件编号 + 实验名：

#### 文件过滤规则

列出前**过滤掉临时文件**（`~$` 开头），这类文件是 Excel 打开时产生的锁定文件，没有实际内容：

```python
import os, glob, unicodedata

def _visual_width(s: str) -> int:
    """中文/全角字符宽度算 2，其余算 1，用于等宽对齐。"""
    return sum(2 if unicodedata.east_asian_width(ch) in ('W', 'F') else 1 for ch in s)

def _pad(s: str, width: int) -> str:
    return s + ' ' * max(0, width - _visual_width(s))

def _fmt_size(n: int) -> str:
    if n < 1024:        return f'{n}B'
    if n < 1024*1024:   return f'{n/1024:.1f}K'
    return f'{n/1024/1024:.1f}M'

files = []
for ext in ('*.csv', '*.txt', '*.xlsx'):
    files.extend(glob.glob(os.path.join(dir_path, ext)))
files = [f for f in files if not os.path.basename(f).startswith('~$')]
files.sort(key=lambda f: os.stat(f).st_birthtime, reverse=True)
files = files[:10]  # 仅展示最近 10 条

# 计算文件名最大可见宽度，统一对齐
name_w = max((_visual_width(os.path.basename(f)) for f in files), default=0) + 2
for i, f in enumerate(files, 1):
    name = os.path.basename(f)
    print(f'{i:2}. {_pad(name, name_w)}{_fmt_size(os.path.getsize(f))}')
```

#### 输出格式

**只展示最近创建的 10 条**（避免 chat UI 折叠）。如果用户要选第 11 条以后的文件，可让其通过自定义输入项填写文件名片段，再做二次过滤。文件名列必须**按可见宽度对齐**（中文字符占 2 列，必须用 `unicodedata.east_asian_width` 计算，不能直接用 `f'{name:<50}'`，否则中文行会错位）。

```
以下是 ~/Downloads 中最近创建的 10 个 CSV/TXT/XLSX 文件（按创建时间倒序）：

 1. 【0512】【测试字段】实验数据分析.xlsx       21.1K
 2. 字段映射测试.csv                          12.3K
 3. 任务ID_84720260.csv                      165.7K
...

（更多历史文件请说明文件名片段，如"找包含 0505 的文件"）
```

#### 用 AskUserQuestion 收集文件 + 实验名

**适用范围**：仅当用户**直接调用 `/nad-acx-pivot-table` 指令**且未在指令所在消息里给出文件线索时走这一步。Step 2.0 的快速通道（自然语言里给出"前 N 个 csv/txt"、"用 xxx.csv/xxx.txt"、"实验名是 XXX" 等）不进入此处。

每次都用 AskUserQuestion 同时打包两个问题（最多 4 个），无条件分支。问题、短标签、选项和说明都必须是中文；例如：

```json
{
  "questions": [
    {
      "header": "\u6587\u4ef6\u9009\u62e9",
      "question": "\u8981\u4f7f\u7528\u54ea\u4e9b\u6587\u4ef6\u751f\u6210\u900f\u89c6\u8868\uff1f",
      "multiSelect": false,
      "options": [
        {"label": "\u524d 3 \u4e2a CSV/TXT", "description": "1,3,4 — a.txt / b.csv / c.txt"},
        {"label": "\u524d 5 \u4e2a CSV/TXT", "description": "1,2,3,4,5\uff08\u8df3\u8fc7 xlsx\uff09"}
      ]
    },
    {
      "header": "\u5b9e\u9a8c\u540d",
      "question": "\u5b9e\u9a8c\u540d\u5982\u4f55\u8bbe\u7f6e\uff1f",
      "multiSelect": false,
      "options": [
        {"label": "\u8df3\u8fc7\uff08\u81ea\u52a8\u547d\u540d\uff09", "description": "\u4f7f\u7528 event_day \u548c exp_id \u81ea\u52a8\u547d\u540d"},
        {"label": "\u81ea\u5b9a\u4e49\u5b9e\u9a8c\u540d", "description": "\u5728\u81ea\u52a8\u8ffd\u52a0\u7684\u8f93\u5165\u9879\u4e2d\u586b\u5199\u5b9e\u9a8c\u540d"}
      ]
    }
  ]
}
```

| questions[0] 文件选择 | questions[1] 实验名 |
|---|---|
| label `"前 3 个 CSV/TXT"`，description 给实际编号 + 文件名（如 `"1,3,4 — a.txt / b.csv / c.txt"`） | label `"跳过（自动命名）"` |
| label `"前 5 个 CSV/TXT"`，description 给编号 + "（跳过 xlsx）" | label `"自定义实验名"` |

特殊情况：
- CSV/TXT 总数 < 5：第二个 label 改为 `"全部 N 个 CSV/TXT"`（N 为实际数量）
- CSV/TXT 总数 ≤ 1：仅留 1 个真实候选 + 1 个保底 label（如 `"包含此 CSV/TXT 加 xlsx 历史追加"`），让自定义输入项兜底
- 选项至少 2 项；**不要把“其他”或“自定义输入”作为显式 label**——AskUserQuestion 会自动追加自定义输入项
- 不要提供“仅第 1 个 / 仅第 2 个”等单文件快捷选项，单文件让用户走自定义输入项

#### 文件编号解析规则

用户回复支持四种格式混合：单个 `1`、逗号 `1,3,5`、范围 `1-4`、混合 `1-4,6`。

```python
def parse_indices(s):
    indices = []
    for part in s.split(','):
        part = part.strip()
        if '-' in part:
            a, b = part.split('-')
            indices.extend(range(int(a), int(b) + 1))
        else:
            indices.append(int(part))
    return sorted(set(indices))
```

> AskUserQuestion 中文转义约束见文档开头的全局约束。不要在 label/description 里写“在自定义输入项中输入”——AskUserQuestion 会自动追加自定义输入项。

支持 CSV、TXT 和 XLSX 混合选择，工具会自动识别格式并合并。TXT 必须是带表头的分隔符文本（支持逗号、Tab、分号、竖线），工具会严格校验表头、行列数和关键数值字段。**读取 XLSX 时会自动按配置中的 `data_sheet_name`（默认"原始数据"）定位数据 sheet**，精确读取，不依赖 sheet 顺序。

### Step 3: 校验文件一致性（多文件时）

如果用户选择了多个 CSV/TXT/XLSX 文件，**必须先校验**：
1. 对 CSV 用 stdlib `csv.reader` + `next()` 只读表头；对 TXT 使用 `pivot_tool.csv_reader.read_txt(path)` 读取并完成分隔符/行列数/数值校验；对 XLSX 用 `read_file(path, sheet_name="原始数据")` 或配置中的 `data_sheet_name` 读取表头
2. 检查所有文件的**字段数量**是否一致
3. 检查所有文件的**字段名称**是否完全一致

> **CRITICAL — 编码嗅探**：厂内导出的 CSV/TXT 不一定是 UTF-8（常见 GBK/GB18030）。**必须按 `utf-8-sig → utf-8 → gbk → gb18030` 顺序逐个尝试**，否则在非 UTF-8 文件上会抛 `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xb5 ...`。这与 `pivot_tool.csv_reader` 内部使用的嗅探顺序一致。

```python
import csv, os

from pivot_tool.csv_reader import read_file, read_txt

def _read_csv_header(path: str) -> list[str]:
    for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
        try:
            with open(path, newline='', encoding=enc) as fh:
                return next(csv.reader(fh))
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("csv", b"", 0, 1, f"无法解码 {path}")

def _read_any_header(path: str) -> list[str]:
    lower = path.lower()
    if lower.endswith('.txt'):
        headers, _ = read_txt(path)
        return headers
    if lower.endswith(('.xlsx', '.xls')):
        headers, _ = read_file(path, sheet_name='原始数据')
        return headers
    return _read_csv_header(path)

headers_per_file = {os.path.basename(f): _read_any_header(f) for f in csv_paths}
```

如果不一致，**停止生成**，向用户展示差异细节：
```
文件字段不一致，无法合并:
  file_a.csv: 12 列 — event_day, cmatch, trans_type, ...
  file_b.csv: 13 列 — event_day, cmatch, ideaid, trans_type, ...
  差异: file_b.csv 多了 ideaid 列
```

引导用户修正后重试。

#### 3a. xlsx 来源校验（硬性限制）

**只接受由本工具生成的 xlsx**（结构特征：恰好 2 个 sheet，其中之一是 `原始数据`，另一个是透视表 sheet——名称由配置中的 `pivot_sheet_name` 决定，默认 `实验组数据透视`，自定义配置也可设为其它）。

校验方法（一次 Python 调用即可）：
```python
import zipfile, re
with zipfile.ZipFile(xlsx_path) as zf:
    wb = zf.read('xl/workbook.xml').decode()
sheet_names = re.findall(r'<sheet[^/]+name="([^"]+)"', wb)
is_pivot_tool_output = len(sheet_names) == 2 and '原始数据' in sheet_names
```

> 不要硬编码透视 sheet 的名字（`数据透视表` / `实验组数据透视` 都可能出现），只校验 `原始数据` 存在 + 总共 2 个 sheet 即可。

**不满足条件时立即拒绝**，不要尝试任何"猜测哪个 sheet 是数据"的诊断行为：

```
该 xlsx 不是本工具生成的（包含 sheet: [...]），无法作为输入合并。
本工具仅支持：
  - CSV 文件
  - TXT 分隔文本文件（逗号、Tab、分号或竖线分隔）
  - 由本工具之前生成的 xlsx（含"原始数据" sheet 用于历史数据追加）
请移除该文件后重试，或将其内容另存为 CSV/TXT。
```

**禁止行为**：
- 不要尝试探测哪个 sheet 像"原始数据"
- 不要写脚本读多个 sheet 看字段
- 不要让用户手动指定 sheet 名

理由：节省工作流轮次，避免在不受支持的输入上浪费时间。

### Step 3.5: 确认字段映射

- **有 `field_map` 配置（包括空字符串）**：直接使用，告知用户「使用已保存的字段映射：`<field_map 值 或 "无映射">`，如需修改请说"修改配置"」，跳过询问
- **无配置（首次）**：展示检测到的字段列表，用 AskUserQuestion 询问是否需要映射：

```
questions[0]: 字段映射确认（multiSelect: false）
  - label: "无需映射"
    description: "检测到字段：event_day, cmatch, trans_type, exp_id, eshow, click, charge, tcharge, conv"
  - label: "自定义映射"
    description: "格式: 原始名:标准名，多个用逗号分隔，如 total_conv:conv,total_charge:charge"
```

- description 中动态填入实际检测到的字段名
- 若用户选择映射，记录映射关系，在 Step 4 校验时先对表头应用映射，再检查必需字段
- 生成命令附加 `--field-map` 参数：

```bash
cd "$SCRIPTS" && python3 -m pivot_tool input.csv -p commercial_ab_test -e "实验名" \
  --field-map "total_conv:conv,total_charge:charge"
```

> **注意**：映射只影响字段识别，不改变透视表中显示的字段名（仍使用标准名称）。

### Step 4: 校验必需字段

读取 CSV/TXT/XLSX 表头后，检查是否包含 Overview 中列出的 **7 个必需字段**（`exp_id`、`event_day`、`eshow`、`click`、`charge`、`tcharge`、`conv`）。

#### 4a. 内置别名表自动匹配（优先尝试）

工具维护一份内置别名表 `pivot_tool/aliases.py` 中的 `FIELD_ALIASES`。**生成命令执行时会自动加载并应用别名**，不需要 LLM 在工作流中显式调用——若 CSV header 精确等于某个登记别名，工具会自动建立映射并在 stdout 输出 `自动应用别名映射: alias→标准名`。

当前已登记的别名（精确相等匹配，区分大小写）：

```
exp_id  ← exp, eid
eshow   ← eshows
click   ← clicks, clk
charge  ← asp_charge
tcharge ← total_target_charge
conv    ← total_convert_num, cv, total_conv
```

工作流中的处理：

- **所有缺失字段都能被内置别名覆盖**：直接进 Step 5，不开 AskUserQuestion，让生成命令在运行时打印 `自动应用别名映射: ...` 即可
- **仍有部分必需字段缺失**：走下面 4b 子串建议流程

#### 4b. 子串建议流程（兜底）

若内置别名仍无法覆盖所有缺失字段，调用 `suggest_field_mapping()` 探测候选：

```python
from pivot_tool.csv_reader import suggest_field_mapping
required = ["exp_id", "event_day", "eshow", "click", "charge", "tcharge", "conv"]
suggestions = suggest_field_mapping(headers, required)
# 例: {"conv": ["merged_conv"], "charge": ["total_charge"]}
```

匹配规则：必需字段名是 CSV 表头的子串（大小写不敏感），且候选不在必需字段集中（避免 `charge` 被误配到 `tcharge`）。

按返回结果分三种处理：

- **每个缺失字段恰有 1 个候选**：用 AskUserQuestion 把推断结果作为默认选项，让用户确认：
  ```
  questions[0]: 字段映射建议（multiSelect: false）
    - label: "使用此映射"
      description: "merged_conv→conv, total_charge→charge"
    - label: "手动覆盖"
      description: "格式: 原始名:标准名，多个用逗号分隔"
  ```
  确认后将映射拼成 `--field-map` 参数传给 Step 6 生成命令。

- **某个缺失字段有多个候选（歧义）**：用 AskUserQuestion 让用户从候选中选一个，每个候选作为一个 label：
  ```
  questions[0]: conv 字段对应哪个？（multiSelect: false）
    - label: "merged_conv"
    - label: "pred_conv"
    - label: "都不是（手动输入）"
  ```

- **零候选（无相似字段）**：**停止生成**，提示：
  ```
  缺少必需字段: eshow, conv（未在数据中找到相似字段）
  您提供的数据不是商业 AB 实验数据，无法使用内置预设生成透视表。
  ```

> **走完 4b 后给用户一个建议**：当通过 `--field-map` 或用户手动确认建立了一个新的非平凡映射（如 `merged_conv → conv`），告知用户：「这是一个常见映射，建议添加到 `pivot_tool/aliases.py` 的 `FIELD_ALIASES["conv"]` 列表中，下次自动命中无需询问」。如果用户同意，直接编辑 aliases.py 追加。

所有必需字段都直接命中或经映射可解析时，进入 Step 5。

### Step 5: 使用 commercial_ab_test 预设

工具只维护**一个**预设 `commercial_ab_test`，声明 7 个必需字段 + 3 个计算字段（`ectr`/`cvr`/`evr`），布局固定为「行：exp_id × 列：13 个数据指标（绝对值 + 相对差）」。

**CSV/TXT 多出来的维度字段**（如 `cmatch`/`mt_id`/`wosid`/`trans_type`/`meg_trade`/`can_predict` 等）会被 `align_config_to_headers` 按值类型自动推断后追加到 pivot cache（`str` → enumerated、`int`/`float` → range），**默认不放入行/列/数据/筛选任何区域**。Excel 打开后可在右侧"数据透视表字段"面板手动拖拽这些新字段做下钻。

> **唯一需要自定义配置的场景**：透视表布局本身要变（比如把 `mt_id` 作为行字段、或额外加筛选维度）。仅仅是"多出几列"或"少一两列可选维度"时直接用预设即可。参考 `references/config_schema.md` 编写自定义 JSON。

### Step 6: 生成透视表

运行命令生成，命名规则：
- 有实验名时: `【MMdd-MMdd】实验名.xlsx`
- 无实验名时降级: `【MMdd-MMdd】【exp_id值】_pivot.xlsx`
- **日期跳跃**：当 `event_day` 存在非连续区间时，每个连续段独立包 `【】`，例如 `0430 + 0503~0509` 且实验名为 `健康竞胜率` → `【0430】【0503-0509】健康竞胜率.xlsx`

```bash
cd "$SCRIPTS" && python3 -m pivot_tool <csv_or_txt_files...> -p <preset> -e "实验名"
```

> **输出参数选择**：交互式调用默认不传 `-o`/`-d`，让工具自动命名到第一个输入文件所在目录；详细规则见上文 [Quick Start 输出路径约定](#quick-start)。

生成后告知用户输出路径和数据行数即可，不需要询问是否打开文件。

### Step 6.5: 保存用户配置

生成成功后，将本次使用的目录和字段映射写入配置文件：

```python
import json, os
config_path = os.path.expanduser('~/.config/iplugin/nad-acx-pivot-table/user_config.json')
os.makedirs(os.path.dirname(config_path), exist_ok=True)
with open(config_path, 'w') as f:
    json.dump({"default_dir": used_dir, "field_map": used_field_map}, f, ensure_ascii=False, indent=2)
```

- `used_dir`：本次使用的目录（如 `~/Downloads`）
- `used_field_map`：本次使用的字段映射字符串（无映射则为空字符串 `""`）
- **首次运行时**：保存后告知用户「已记住您的偏好设置（目录：`<dir>`），下次无需重新选择。如需修改请说"修改配置"」
- **非首次运行**：静默保存，不提示

## 其他场景

### 外部 agent / 自动化脚本调用约定

非交互式调用方需要固定输出位置时，**优先用 `-d <目录> -e "<实验名>"`**（文件名仍按 `【MMdd-MMdd】实验名.xlsx` 自动生成）。仅在确需固定文件名时才用 `-o <完整路径>`——此时 `-e` 不会拼入文件名，工具在 stderr 输出警告但不阻塞。详细约定见上文 Quick Start 的"输出路径约定"。

### 追加新数据（已有透视表 + 新 CSV/TXT）

当 SQL 导出有行数限制、需要分批导出并追加到已有分析文件时：

1. 选择之前生成的透视表 xlsx（工具自动读取其中的"原始数据" sheet）
2. 同时选择新的 CSV/TXT 文件
3. 工具合并历史数据 + 新数据，重新生成透视表

```bash
cd "$SCRIPTS" && python3 -m pivot_tool old_pivot.xlsx new_data.txt -p commercial_ab_test -e "实验名"
```

**注意**: 仅支持读取由本工具生成的 xlsx（包含"原始数据" sheet）。如果 xlsx 来自其他来源，sheet 名称可能不同，需通过 `read_file(path, sheet_name="...")` Python 接口指定。

### 多业务合并（一个实验号多个业务方）

当同一实验号下有多个业务方 CSV，且需要放进同一个 xlsx（每个业务 2 个 sheet：透视 + 明细）时，
使用 `merge_pivots` 模块，不再手拼多透视表工作簿：

```bash
cd "$SCRIPTS" && python3 -m pivot_tool.merge_pivots \
  health_cover.csv health_cover.json \
  health_mall.csv health_mall.json \
  fengchao.csv fengchao.json \
  agent.csv agent.json \
  exposure.csv exposure.json \
  lead_live.csv lead_live.json \
  --hide-data-sheets \
  -o "【0801-0803】【166762】WebPanel半屏统一_原生数据透视表.xlsx"
```

- 输入为 `CSV 配置` 交替传参，顺序即工作簿 sheet 顺序
- 每个业务必须有自己的 JSON 配置（`data_sheet_name`/`pivot_sheet_name` 用业务名区分）
- 合并入口与单透视表一致：自动处理内置字段别名，并将与计算字段同名的原始列重命名为 `*_source`
- 默认保留明细 sheet 可见；需要仅展示透视页时传 `--hide-data-sheets`
- 0 行 CSV 会生成「暂无数据」普通占位 sheet，不注册空 pivot/cache，避免 Excel 修复提示
- 输出先写同目录临时文件，所有原生透视表通过 OOXML 闸门后再原子替换目标文件
- 生成后建议用 Excel 打开验证；LibreOffice 对 6 个以上原生透视表的兼容性有限，可能只显示部分透视表，但 Excel 正常

编程接口：

```python
from pivot_tool.merge_pivots import create_multi_business_pivot

create_multi_business_pivot(
    [
        ("health_cover.csv", "health_cover.json"),
        ("agent.csv", "agent.json"),
    ],
    "output.xlsx",
    hide_data_sheets=True,
)
```

### 自定义透视表配置

1. 读取用户的 CSV/TXT/XLSX 表头，了解数据结构
2. 参考 `references/config_schema.md` 了解完整配置 schema
3. 为用户编写 JSON 配置文件，需定义：
   - `columns`: 每列的名称、类型（str/int/float）、是否可空、sharedItems 类型
   - `calculated_fields`: 计算字段（公式基于已有列）
   - `pivot_layout`: 行字段、列字段、数据字段（含聚合方式）、筛选字段
4. 运行 `cd "$SCRIPTS" && python3 -m pivot_tool <csv_or_txt> --config <json> -o <output>`

### 新增预设

1. 按自定义配置流程编写 JSON 配置
2. 将配置保存到 `pivot_tool/presets/<name>.json`
3. 后续即可通过 `--preset <name>` 复用

## pivot_tool 包结构

工具位于当前 skill 的 `scripts/pivot_tool/` 目录：

```
pivot_tool/
├── __init__.py          # 包入口
├── __main__.py          # CLI 入口 (argparse)
├── config.py            # 配置 dataclass + JSON 加载 + 校验
├── csv_reader.py        # CSV/TXT/XLSX 读取 + 字段分析 (FieldMaps)
├── aliases.py           # 必需字段的内置别名表 (FIELD_ALIASES)
├── xml_utils.py         # XML 工具函数 + 命名空间常量
├── shared_strings.py    # 共享字符串构建器
├── data_sheet.py        # 数据工作表构建器
├── pivot_cache.py       # 缓存定义 + 缓存记录构建器
├── pivot_table.py       # 透视表定义构建器
├── ooxml_guard.py       # 生成后 PivotTable OOXML 兼容性闸门
├── static_xml.py        # 静态 XML 模板
├── packager.py          # 组装器 → 写 zip
└── presets/
    ├── __init__.py      # 预设注册
    └── commercial_ab_test.json
```

## 配置 JSON Schema

详细字段定义（columns / calculated_fields / pivot_layout / shared_items_type / show_data_as 等）见 `references/config_schema.md`。

## 编程接口

除 CLI 外，也可在 Python 中直接调用：

```python
from pivot_tool.config import load_preset, load_config
from pivot_tool.packager import create_xlsx_with_pivot

config = load_preset("commercial_ab_test")
# 或: config = load_config("my_config.json")
create_xlsx_with_pivot("input.csv", None, config, exp_name="流量优化")
# 自动生成: 【0419-0422】流量优化.xlsx
```

## 注意事项

- 零外部依赖：仅使用 Python 标准库（csv, zipfile, argparse, json, dataclasses）
- 生成的 xlsx 需在 Excel（或兼容 OOXML 的软件）中打开，WPS 兼容性可能有限
- 计算字段公式语法为 OOXML 格式（如 `click / eshow`，用空格分隔字段名和运算符）
- **修改 `pivot_tool/` 代码前必读 `references/ooxml_pitfalls.md`** — 记录 Excel 兼容性约束（refreshOnLoad、colFields、firstDataRow、pageFields、占位符容错、属性顺序、枚举 items 等）。**仅在 Agent 被要求修改 `pivot_tool/*.py` 时才读**，常规生成透视表的工作流不需要加载，避免占用上下文。
