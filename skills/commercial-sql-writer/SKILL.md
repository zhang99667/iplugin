---
name: commercial-sql-writer
version: 0.1.1
description: 商业广告 SQL 写作助手。当用户要求编写、改写或检查商业/NAD 广告分析 SQL，或提到展点消转、大盘、cmatch、实验分组、消费、转化、目标成本、下载漏斗、调起、半屏、优惠券、私信、预渲染、落地页性能、落地页抵达率、问题下钻等数据需求时触发。优先基于商业大盘展点消转母版做最小改写，再做需求拆解、表/字段选择、指标口径确认和 SQL 自查。只替换实验号或日期时使用 sql-exp-replace，不使用本技能。
tags: [sql, commercial, ads, nad, hive, spark, analytics]
user_invocable: true
---

# Commercial SQL Writer

目标：为商业广告数据分析需求编写、改写和检查 Hive/Spark SQL。多数需求应围绕商业大盘展点消转母版做最小改写，而不是完全重写 SQL；先判断业务场景、相关表字段、指标口径和 join 方式，再生成可跑、口径清楚、便于替换日期和实验号的 SQL。

## 触发边界

### 适用

- 用户要求写商业广告 SQL、NAD SQL、展点消转 SQL、展点消 SQL、大盘 SQL。
- 用户要把历史 SQL 改成新需求、新实验、新日期、新维度或新口径。
- 用户要求检查 SQL 的表选择、join key、实验分组、分区过滤、消费/转化/目标成本口径。
- 需求涉及 `cmatch`、`event_type`、`ovl_exp`、`ovl_id`、`ovid_eid_list`、`searchid`、`idea_id`、`trans_type`、`wosid`、`mt_id`、`place_id` 等商业广告字段。
- 场景涉及下载漏斗、调起、半屏、优惠券、私信、预渲染、落地页性能/抵达率、按 `userid` / `search_id` / `ideaid` 下钻排查。

### 不适用

- 只替换实验号、日期范围或 CASE 标签：使用 `sql-exp-replace`。
- 需要实际跑数、下载 DataPilot 结果或生成透视表：使用 DataPilot / pivot 相关能力。
- 普通非商业广告 SQL，除非用户明确要求复用商业广告表和口径。
- 只解释 SQL 且不需要生成、改写或检查时，直接回答即可。

### 需要确认

如果缺少日期范围、业务范围、指标、维度、端类型、实验组/对照组、`cmatch` / `event_type` 或目标表，先问最少问题。能从上下文合理推断时，可以先列出假设再给 SQL。

## Reference 路由

- 表、字段、主键、分区不确定时，读取 `references/table-guide.md`。
- 涉及 `charge`、`conv`、`tcharge`、`ctr`、`ecpm`、深转或目标成本时，读取 `references/metric-rules.md`。
- 要生成完整 SQL 或改写历史 SQL 时，读取 `references/query-patterns.md`。
- 出现半屏、优惠券、私信、下载、调起、预渲染、落地页性能/抵达率、问题排查等场景词时，读取 `references/scenario-router.md`。
- 输出前按 `references/checklist.md` 自查。

## 工作流程

1. 拆需求：提取日期、流量范围、端、`cmatch` / `event_type`、实验分组、维度、指标、下钻粒度。
2. 优先选择大盘展点消转母版：如果用户需求能落到曝光、点击、消费、转化、目标成本，先保留 `t1(asp 展点消) LEFT JOIN t2(转化/目标成本)` 的母版结构。
3. 做 schema linking：只加载本次相关表和字段，不把全部 schema 或全部示例 SQL 塞进上下文。
4. 选主表：
   - 展点消优先 `fc_nad.nativeads_feed_asp_view`。
   - 客户端行为事件优先 `fc_nad.nativeads_ods_als_common` 或 `fc_nad.nativeads_ods_als_normal`。
   - 转化和目标成本按场景选择 OCPX、视频转化或 all_convert 相关表。
5. 确认 join key：`asp_view.searchid_decimal` 对其他表的 `search_id`；注意 `ideaid` / `idea_id` 字段名差异。
6. 套指标口径：消费单位、深转逻辑、目标成本、转化数、CTR、ECPM 都按商业规则计算。
7. 写 SQL：优先在母版 SQL 上局部替换日期、实验号、`event_type`、`cmatch`、维度和覆盖/命中过滤；确实需要重构时再使用 CTE。
8. 自查并修正：重点检查分区、实验字段、join key、单位换算、除零、字段类型和扫描范围。

## 输出要求

- 用户要 SQL 时，优先直接输出 SQL 代码块。
- 如果存在假设，SQL 前最多列 3 条关键假设。
- 改写历史 SQL 时，保持原 SQL 风格和业务逻辑，只改必要部分。
- 用户提供历史大盘 SQL 或覆盖部分 SQL 时，不要完全重写；优先 patch 原 SQL 的过滤、维度、命中集合和聚合字段。
- 检查 SQL 时，先列风险点，再给修正片段或完整 SQL。
- 不伪造字段；字段不确定时说明需要查 schema 或让用户确认。
