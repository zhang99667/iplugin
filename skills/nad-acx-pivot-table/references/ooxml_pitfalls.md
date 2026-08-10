# OOXML 踩坑记录

修改 `pivot_tool/` 代码前必读。这些约束违反后会导致 Excel 打不开、布局异常或透视表为空白。

生成器写完 xlsx 后会自动调用 `pivot_tool.ooxml_guard.assert_valid_pivot_xlsx()`。如果修改了 `pivot_cache.py`、`pivot_table.py`、`static_xml.py` 或相关配置结构，必须额外手动运行：

```bash
cd skills/nad-acx-pivot-table/scripts
python3 -m pivot_tool.ooxml_guard <output.xlsx>
```

这个闸门不是完整 Excel 渲染器，但会检查本文件沉淀过的高风险结构：工作簿 `styles.xml` 与 Normal 命名样式、`refreshOnLoad`、多数据字段的 `colFields/-2` 与 `colItems`、页面筛选字段的 `pageFields hier="-1"`、枚举字段 `items` 覆盖、字符串枚举大小写重复、计算字段属性顺序等。

## 1. refreshOnLoad — 打开时自动刷新

`pivotCacheDefinition` 必须包含 `refreshOnLoad="1"` 属性。否则打开 xlsx 后透视表为空白，需手动右键刷新。

原因：sheet1.xml 的 `<sheetData/>` 是空的（不预计算单元格值），需要 Excel 在打开时从 cacheRecords 重新计算。

## 2. colFields 不可省略 — Values 标签行是必要的

当有多个数据字段作为列展开时，`colFields` 必须包含 `<field x="-2"/>`，同时必须生成对应的 `colItems`。如果省略 `colFields`/`colItems` 试图消除第一行的 "Values" 标签行，Excel 会报错（"发现部分内容有问题"）或无法打开。

第一行的 "Values" 标签行是 Excel 透视表在多数据字段列模式下的**固有行为**，在 Excel 中手动创建同样结构的透视表也会有这一行。该行有功能性：点击可切换数据字段的排列。

## 3. location ref 必须避开 pageFields 页面区

`location@ref` 只描述透视表主体，不包含页面筛选区。页面筛选字段默认纵向排列：

- N 个 `pageFields` 占主体上方 N 行，并与主体间隔 1 个空行；主体首行至少为 `N + 2`
- 有页面筛选字段时，`location` 必须写 `rowPageCount="N" colPageCount="1"`，且 `firstDataRow="1"`
- 无页面筛选字段时保留普通布局：主体从 A1 开始；`colFields` 含 `<field x="-2"/>` 时 `firstDataRow="2"`，否则为 `1`
- `ref` 范围高度必须等于 `firstDataRow + rowItems count`

例如两个筛选字段、两个枚举行项加总计、三个横向数据字段时，正确主体为：

```xml
<location ref="A4:D7" firstHeaderRow="0" firstDataRow="1" firstDataCol="1"
          rowPageCount="2" colPageCount="1"/>
```

错误地写成 `A1:D5 firstDataRow="2"` 会让页面筛选区与透视主体重叠。此类文件 ZIP/XML 均可解析，旧 guard 也可能误判通过，但 Microsoft Excel 打开时会提示修复。该布局已用真实 Excel 重复打开和 LibreOffice OOXML 正规化结果交叉验证。

## 4. filter_fields 必须同时生成 pageFields

如果某个字段在 `pivotFields` 中声明了 `axis="axisPage"`，必须在 `pivotTableDefinition` 中生成对应的 `<pageFields>`：

```xml
<pageFields count="1"><pageField fld="0" hier="-1"/></pageFields>
```

只给 `pivotField` 标记 `axisPage`，但省略 `<pageFields>`，会让 Excel 判定透视表定义不完整。`pageField` 本身也要带 `hier="-1"`；真实 Excel 生成的页面筛选字段会写这个属性，缺失时 Mac Excel 仍可能提示修复。此类文件常见表现是 ZIP 结构正常、`openpyxl` 可读取，但 Excel 打开时提示修复或删除 `pivotTable1.xml`。

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

## 11. 多透视表必须逐个校验 cacheId 与关系

多业务工作簿中，不能只校验 `pivotTable1.xml`。每个 `pivotTableDefinition@cacheId`
都必须对应 `workbook.xml` 中的唯一 `pivotCache@cacheId`，后者的 `r:id`
必须通过 `workbook.xml.rels` 指向实际存在的 cache definition。每个透视表、
cache definition 和 cache records 也必须各自具备完整的 `.rels` 关系。

`merge_pivots` 可以跳过 0 行业务的 pivot/cache，因此部件编号可能不连续；
校验器必须从实际 OOXML 关系发现部件，不能假设它们是 `1..N` 连续序列。

## 12. styles.xml 必须包含 Normal 命名样式

工作簿必须通过 `workbook.xml.rels` 唯一引用 `styles.xml`，并在
`[Content_Types].xml` 中声明 styles Content Type。最小样式表必须按规范顺序包含：

```xml
<cellStyleXfs count="1"><xf .../></cellStyleXfs>
<cellXfs count="1"><xf ... xfId="0"/></cellXfs>
<cellStyles count="1">
  <cellStyle name="Normal" xfId="0" builtinId="0"/>
</cellStyles>
```

仅有 `cellStyleXfs[0]` 不等于声明了 Normal 样式。缺少 `cellStyles/Normal`
时，Mac Excel 可能提示“发现部分内容有问题”，并在恢复日志中删除
`workbook.xml` 的样式记录。guard 还必须检查各集合 `count`、`fontId`、
`fillId`、`borderId`、`xfId` 的边界以及 styleSheet 子元素顺序。
