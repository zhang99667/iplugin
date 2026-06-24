# OOXML 踩坑记录

修改 `pivot_tool/` 代码前必读。这些约束违反后会导致 Excel 打不开、布局异常或透视表为空白。

## 1. refreshOnLoad — 打开时自动刷新

`pivotCacheDefinition` 必须包含 `refreshOnLoad="1"` 属性。否则打开 xlsx 后透视表为空白，需手动右键刷新。

原因：sheet1.xml 的 `<sheetData/>` 是空的（不预计算单元格值），需要 Excel 在打开时从 cacheRecords 重新计算。

## 2. colFields 不可省略 — Values 标签行是必要的

当有多个数据字段作为列展开时，`colFields` 必须包含 `<field x="-2"/>`，同时必须生成对应的 `colItems`。如果省略 `colFields`/`colItems` 试图消除第一行的 "Values" 标签行，Excel 会报错（"发现部分内容有问题"）或无法打开。

第一行的 "Values" 标签行是 Excel 透视表在多数据字段列模式下的**固有行为**，在 Excel 中手动创建同样结构的透视表也会有这一行。该行有功能性：点击可切换数据字段的排列。

## 3. location ref 与 firstDataRow 必须匹配

- `colFields` 含 `<field x="-2"/>` 时，Excel 渲染 **2 行表头**（Values 标签行 + 数据字段名行），此时 `firstDataRow` 必须为 `2`
- 无 `colFields` 时只需 1 行表头，`firstDataRow` 为 `1`
- `ref` 范围的总行数 = `num_header_rows + num_data_rows + 1(grand total)`
- 如果行数不匹配，会导致空白行或 Excel 报错

## 4. filter_fields 必须同时生成 pageFields

如果某个字段在 `pivotFields` 中声明了 `axis="axisPage"`，必须在 `pivotTableDefinition` 中生成对应的 `<pageFields>`：

```xml
<pageFields count="1"><pageField fld="0"/></pageFields>
```

只给 `pivotField` 标记 `axisPage`，但省略 `<pageFields>`，会让 Excel 判定透视表定义不完整。此类文件常见表现是 ZIP 结构正常、`openpyxl` 可读取，但 Excel 打开时提示修复或删除 `pivotTable1.xml`。

`pageFields` 在 XML 顺序上应放在 `colItems` 之后、`dataFields` 之前。

## 6. 字符串枚举字段的空值必须显式化（Strategy Z）

**规则**：对字符串类型的枚举 cacheField，若原始数据含空值，不能使用 `containsBlank="1"` + 记录里 `<m/>` + pivotField `<item t="blank"/>` 的组合。Excel 会判定整个 pivotTable 部件结构损坏，直接删除，并连带清空 workbook.xml 的 `<pivotCaches>` 引用。

**正确做法**：把空字符串作为显式枚举项 `<s v=""/>` 追加到 sharedItems，`item_index_maps[""] = N`，所有记录单元用 `<x v="N"/>`，sharedItems 去掉 containsBlank。此时 pivotField items 也不需要 `<item t="blank"/>`，空值通过普通 `<item x="N"/>` 覆盖。

代码实现：`csv_reader.analyze_fields` 在字符串枚举 + `has_blanks` 场景下把 `""` 追加到 `enumerated_items`/`item_index_maps` 并把 `has_blanks[i]` 清零；`pivot_cache._encode_cell` 的字符串枚举分支优先走 `item_index_maps` 查表。

数值枚举字段（如 event_day）不受此规则约束——走 containsBlank + `<m/>` + `<item t="blank"/>` 路径仍然合法。

## 7. pivotField items 必须覆盖所有枚举字段

凡是 `sharedItems` 以 `count="N"` 方式声明的枚举字段（不论是否放入 row/col/data/filter 任一 axis），对应 pivotField **都必须生成 `<items>` 列表**：

- N 个 `<item x="i"/>`（i=0..N-1，或按 row_item_order 指定顺序）
- 末尾追加一个 `<item t="default"/>`
- `items count` = N + 1（字符串枚举用 Strategy Z 后，空值已并入 N，无需额外 `<item t="blank"/>`）

**反面教训**：曾尝试"只对 axis 上的字段生成 items，非 axis 字段留空 `<pivotField showAll="0"/>`"。结果 Excel 打开时直接删除整个 pivotTable1.xml，连锁导致 workbook.xml 的 `<pivotCaches>` 引用被清空。原因是 Excel 对枚举 cacheField 预期 pivotField 必有对应 items；缺失会被判为结构损坏。

## 8. 字符串枚举项去重必须大小写不敏感

**规则**：同一字符串 cacheField 的 sharedItems 不能同时出现仅大小写不同的两个项（如 `leftslide` 与 `leftSlide`）。Excel 对 sharedItems 的字符串比较是 case-insensitive，会把它们判定为重复枚举项，直接删除整个 pivotTable（且同样连锁清空 workbook.xml 的 `<pivotCaches>`）。

**正确做法**：`csv_reader._unique_ordered` 对字符串列按 `v.casefold()` 去重，保留首次出现的原始大小写作为展示项；`item_index_maps` 也用 casefold 作键，`_encode_cell` 用 `val.casefold()` 查表，把后续不同大小写的记录映射到同一索引。

**定位方法**：报错特征为 Excel 打开时提示「已删除的功能: /xl/pivotTables/pivotTable1.xml 部分的 数据透视表」+「已删除的记录: /xl/workbook.xml 部分的 工作簿属性」。用 `{v.casefold() for v in sharedItems values}` 统计去重数，若 < 原始 count 即触发此陷阱。

## 9. int/float 列可能含非数值占位符

CSV 中 int/float 类型列的值可能出现：
- `"13.0"` 而非 `"13"`（pandas 导出常见）→ 需 `int(float(val))` 两步转换
- `"-"` 等非数值占位符（SQL 查询无数据时填充）→ 需用 `try/except (ValueError, TypeError)` 跳过

`_col_stats`、`_unique_ordered`、`data_sheet.build_data_sheet_xml` 三处均需容错处理，否则遇到含占位符的列时会崩溃。

## 10. pivotField 属性顺序

计算字段的 pivotField 属性必须按此顺序排列：`dataField="1" dragToRow="0" dragToCol="0" dragToPage="0" showAll="0" defaultSubtotal="0"`。`showAll` 必须在 `dragToPage` 之后、`defaultSubtotal` 之前，否则与原脚本生成的 XML 不一致。
