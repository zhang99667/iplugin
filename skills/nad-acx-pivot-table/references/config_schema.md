# 配置 JSON Schema 参考

## 完整配置结构

```json
{
  "name": "配置名称",
  "description": "配置描述",
  "data_sheet_name": "原始数据",
  "pivot_table_name": "数据透视表",
  "pivot_style": "PivotStyleLight16",
  "columns": [...],
  "calculated_fields": [...],
  "pivot_layout": {...}
}
```

## columns — 列定义

每个列定义对应 CSV 的一列，按顺序排列。

```json
{
  "name": "列名",
  "type": "str|int|float",
  "nullable": false,
  "shared_items_type": "auto|enumerated|range|mixed"
}
```

### 字段说明

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | string | (必填) | 列名，必须与 CSV 表头一致 |
| `type` | string | (必填) | `"str"`: 字符串（用共享字符串编码）<br>`"int"`: 整数<br>`"float"`: 浮点数 |
| `nullable` | bool | `false` | 是否允许空值。影响 cacheField 的 `containsBlank` 属性 |
| `shared_items_type` | string | `"auto"` | 控制 cacheField 中 sharedItems 的生成方式 |

### shared_items_type 详解

- **`auto`** (默认): `str` 类型自动用 `enumerated`，`int`/`float` 自动用 `range`
- **`enumerated`**: 生成枚举值列表。适用于维度字段（如日期、实验组 ID）。在 cacheRecord 中用 `<x v="索引"/>` 编码
  - `int` 枚举：`<sharedItems><n v="20240101"/><n v="20240102"/>...</sharedItems>`
  - `str` 枚举：`<sharedItems><s v="dz"/><s v="exp"/>...</sharedItems>`
- **`range`**: 仅生成 `minValue`/`maxValue`。适用于度量字段。在 cacheRecord 中用 `<n v="值"/>` 编码
- **`mixed`**: 含混合类型数据（同时有字符串和数字）。适用于像 `mt_id` 这样可能含 `#` 前缀的字段。生成 `containsMixedTypes="1"` 属性

## calculated_fields — 计算字段

计算字段在透视表中动态计算，不存在于 CSV 原始数据中。

```json
{
  "name": "ectr",
  "formula": "click /eshow"
}
```

### 公式语法

- OOXML 格式：`字段名 运算符 字段名`
- 运算符前后用空格分隔
- 支持的运算符：`+` `-` `*` `/`
- 示例：`"click /eshow"` 表示 click 除以 eshow

## pivot_layout — 透视表布局

```json
{
  "row_fields": ["exp_id"],
  "col_fields": ["__data__"],
  "filter_fields": [],
  "data_fields": [...],
  "row_item_order": {
    "exp_id": ["dz", "exp"]
  }
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `row_fields` | list[str] | 放在行区域的字段名（引用 columns 中的 name） |
| `col_fields` | list[str] | 放在列区域的字段名。特殊值 `"__data__"` 表示数据字段标签 |
| `filter_fields` | list[str] | 放在筛选区域的字段名；生成器会同时写入 `axisPage` 与 `pageFields` |
| `data_fields` | list[DataFieldDef] | 数据区域字段定义（见下方） |
| `row_item_order` | dict | 可选。指定行字段值的显示顺序 |

### data_fields — 数据字段定义

```json
{
  "name": "求和项:eshow",
  "source_field": "eshow",
  "aggregation": "sum",
  "show_data_as": "normal",
  "base_field": null,
  "base_item": 0,
  "num_fmt_id": 0
}
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | string | (必填) | 在透视表中显示的名称 |
| `source_field` | string | (必填) | 来源字段名（可引用列名或计算字段名） |
| `aggregation` | string | `"sum"` | 聚合方式（sum, count, average, max, min） |
| `show_data_as` | string | `"normal"` | `"normal"`: 原始聚合值<br>`"percentDiff"`: 相对基准项的百分比差异 |
| `base_field` | string\|null | `null` | percentDiff 时的基准字段名 |
| `base_item` | int | `0` | 基准项索引（0 表示第一个枚举值） |
| `num_fmt_id` | int | `0` | 数字格式 ID。`0`=常规，`10`=百分比 |

## 完整示例：commercial_ab_test 预设

此预设用于商业广告 AB 实验数据分析（工具内**唯一**预设；CSV 多出来的维度字段会被 `align_config_to_headers` 自动追加到 pivot cache，可在 Excel 字段面板手动拖拽）：

- **7 个必需字段**: event_day, exp_id, eshow, click, charge, tcharge, conv（字段名严格相等，同义别名通过 `pivot_tool/aliases.py` 自动映射）
- **3 个计算字段**: ectr (点击率), cvr (转化率), evr (展现转化率)
- **13 个数据字段**: eshow/click/charge/tcharge/conv 的绝对值 + 相对差，ectr/cvr/evr 的相对差
- **行字段**: exp_id（dz=对照组, exp=实验组）
- **列字段**: `__data__`（数据字段标签横向展开）

预设文件位于: `pivot_tool/presets/commercial_ab_test.json`

## CLI 用法

### 多文件合并

支持传入多个 CSV/XLSX 文件路径，工具会自动校验表头一致性并拼接所有行。适用于 SQL 导出因行数限制拆分为多个文件的场景。

```bash
python3 -m pivot_tool a.csv b.csv c.csv --preset commercial_ab_test
```

也支持 glob 模式：

```bash
python3 -m pivot_tool /path/to/*.csv -c my_config.json
```

**注意**: 多文件合并要求所有 CSV 文件的表头完全一致，否则会报 `ValueError: 表头不一致` 错误。

### 自动命名

当不指定 `-o` 输出路径时，工具会从数据中自动生成文件名：

- 有实验名（`-e`）时: `【MMdd-MMdd】实验名.xlsx`
- 无实验名时降级: `【MMdd-MMdd】【exp_id值】_pivot.xlsx`
- `event_day` 含日期跳跃时每段独立包 `【】`，如 `【0430】【0503-0509】健康竞胜率.xlsx`
- 输出目录优先用 `-d`，否则与第一个输入文件相同

如果配置中没有 `event_day` 列，则降级为 `pivot_pivot.xlsx`。

## Python 类型定义

配置在代码中对应以下 dataclass（定义在 `pivot_tool/config.py`）：

- `ColumnDef` — 列定义
- `CalculatedFieldDef` — 计算字段定义
- `DataFieldDef` — 数据字段定义
- `PivotLayoutDef` — 透视表布局定义
- `PivotConfig` — 顶层配置

关键便利方法：
- `config.column_index(name)` — 按名称查找列索引
- `config.field_index(name)` — 查找 cacheField 索引（含计算字段）
- `config.str_col_indices` / `config.int_col_indices` — 按类型过滤的列索引集合
- `config.total_field_count` — 总字段数（列 + 计算字段）
