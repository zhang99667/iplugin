# 商业 SQL 输出前自查

生成、改写或检查 SQL 后，按这份清单快速过一遍。发现风险时先修正；不能确认时明确告诉用户。

## 需求完整性

- 日期范围是否明确。
- 用户要的是汇总趋势、实验对比、转化目标成本、漏斗，还是排查明细。
- 用户说“大盘”时，是否默认理解为展点消转：`eshow/click/charge/convert_num/target_charge`，而不是只给单表展点消。
- 维度是否齐全：天、端、`cmatch`、`event_type`、实验分组、`trans_type`、页面、区域、样式、广告主。
- 是否需要实验组/对照组，实验字段在哪些表里分别是什么。

## 表与字段

- 展点消是否使用 `fc_nad.nativeads_feed_asp_view`。
- 行为事件是否使用 ALS common / normal 或用户明确的日志表。
- 落地页性能/抵达率是否使用 `fc_nad.nativeads_als_every_log`，并确认 `category_id = '1029'` 下 `f*` / `ef*` 字段映射。
- 转化是否选对 OCPX、视频转化或 all_convert 表。
- `asp_view.ideaid` 和其他表 `idea_id` 是否区分。
- 没有把不确定字段当作已知字段输出。

## 分区和扫描范围

- 大表是否带 `event_day`。
- `nativeads_feed_asp_view` 是否尽量带 `event_type`。
- `cmatch = '719'` 是否同步使用 `event_type = 'browser'`；`cmatch = '545'` 是否按上下文使用 `event_type = 'shoubai'`。
- 是否按场景补了 `cmatch`、`log_type`、`page`、`product_id`、`wosid` / `os_type`。
- 落地页性能日志中 `cmatch` 是否使用 `f7`，URL 是否使用 `f2`，没有把 `category_id = '1029'` 当成 `cmatch`。
- 排查 SQL 是否限制了用户、`search_id`、日期或样本量。

## Join

- `asp_view` join 其他表是否使用 `searchid_decimal = search_id`。
- 是否同时 join `idea_id` 和 `event_day`。
- 行为表多事件是否先去重，避免放大展点消。
- LEFT JOIN / INNER JOIN 是否符合业务：命中 PV 回看通常从命中集合出发；大盘补转化通常从 asp LEFT JOIN 转化。

## 指标

- `charge` 是否按 `bid_type` / `pricing_type` 分支，并最终转元。
- 当前 SQL 是大盘聚合还是计费记录明细：大盘常用 `clk * price / 100`，计费记录明细可用 `price / 100` 或 CPM-like `price / 100000`。
- 小时级 SQL 是否考虑 CPC 按计费时间落盘，而非 ASP 检索时间落盘。
- `click` 是否用 `clk AS click` 或聚合 `SUM(clk)`。
- `ctr`、`ecpm`、转化率是否处理分母为 0。
- 落地页抵达率是否处理分母为 0；抵达条件是否同时要求 `ef2` / `ef3` 合法、`ef3 >= ef2`、时间差小于阈值。
- 转化是否过滤 `convert_num IS NOT NULL` 和 `convert_num != '0'`。
- 深转和浅转合并逻辑是否符合需求。
- `convert_type_list` 分隔符是否按表区分：OCPX 常见 `\002`，视频转化常见 `#`。
- `tcharge` 是否用 bid * conv / 100，而不是套 asp 消费公式。

## 实验分组

- `ovl_exp`、`ovl_id`、`ovid_eid_list`、`eid_list` 是否分别处理。
- `-0` / `-dz` 命名是否和用户实验约定一致。
- CASE 分组和 WHERE 过滤是否一致。
- 跨表实验过滤是否没有遗漏。

## SQL 形态

- 是否优先保留商业大盘展点消转母版，而不是完全重写。
- 如果是覆盖部分/命中部分，是否把命中集合内联到 `t1` 或用 `hit_pv` join `t1`，并继续复用原 `t2` 转化目标成本。
- 复杂 SQL 是否用 CTE 拆解。
- 聚合字段是否都在 `GROUP BY` 或聚合函数中。
- 字段是 STRING 时，数值计算是否显式 `CAST`。
- 保留了日期、实验号、`cmatch` 等易改条件。
- 改写历史 SQL 时没有无关重构。
- 使用 `nativeads_als_every_log` 直接 `COUNT(*)` 时，是否向用户说明未去重可能偏大；若用户要求去重，是否按 `cuid + ef2` 或 `f8 + f6` 等业务口径处理。

## 对账和排查

- 如果 CPM 曝光在 `asp_view` 中明显少于 ALS 曝光，先检查 join 是否正确：ALS 的 `search_id` 应 join `asp_view.searchid_decimal`，并同时 join `idea_id` / `ideaid`。
- CPM 相关差异还可能来自计费日志过滤；需要时去 CPM charge 表按 `chg_tag`、`ign_info` 等字段看是否被过滤。
- 对账 SQL 尽量先抽 `unit_id`、`search_id`、`idea_id`、`cmatch`、`event_day`、`event_hour` 明细，不要直接只看大盘聚合。
