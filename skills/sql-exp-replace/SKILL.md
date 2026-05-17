---
name: sql-exp-replace
version: 0.1.0
tags: [sql, data, experiment]
description: 替换SQL中的实验号和日期。当用户提供SQL并要求修改实验分组（ovl_exp/ovl_id/ovid_eid_list等实验号）或日期范围时触发。支持批量替换CASE分组逻辑、WHERE过滤条件中的实验号，以及所有event_day日期。
user_invocable: true
---

# SQL 实验号与日期替换

## 功能

帮助用户快速替换广告投放实验SQL中的：
1. **实验号**：ovl_exp / ovl_id / ovid_eid_list 等字段中的实验分组编号
2. **日期范围**：所有 event_day 的 between 日期

## 使用方式

用户提供：
- 原始 SQL
- 新的实验号分组（实验组+对照组）
- 新的日期范围

## 替换规则

### 实验号替换

实验号通常出现在以下位置，**所有位置都必须同步替换**：

1. **CASE 分组逻辑**（exp_id / ovl 字段）：
   - `array_contains(split(ovl_exp, "#"), "XXXXX-0")` 格式
   - `ovl_exp like '%XXXXX-0%'` 格式
   - 同一个实验号 `XXXXX-0` 是实验组，`XXXXX-dz` 是对照组

2. **WHERE 过滤条件**：
   - `ovl_exp LIKE '%XXXXX-0%'` 或 `array_contains(...)` 格式
   - `ovl_id like '%XXXXX-0%'`
   - `ovid_eid_list LIKE '%XXXXX-0%'`

3. **实验分组命名规则**：
   - 同一实验号的 `-0` 后缀是实验组，`-dz` 后缀是对照组
   - 例如：162159-0（实验）和 162159-dz（对照）是一组
   - 每个实验组都有各自对应的对照组

### 日期替换

替换所有 `event_day between "YYYYMMDD" and "YYYYMMDD"` 中的日期，包括：
- 主查询的 event_day
- 所有子查询中的 event_day
- 注意保留日期格式（带引号的 "YYYYMMDD"）

## 注意事项

1. **不修改其他逻辑**：只替换实验号和日期，不改动SQL的业务逻辑、字段、表名等
2. **完整替换**：SQL中所有出现实验号的位置都要替换，不能遗漏
3. **保持格式**：替换后保持原SQL的缩进和格式风格
4. **确认对照组**：每个实验组对应自己的对照组（同实验号-dz），不要混用
5. **直接输出**：替换完成后直接以代码块形式输出完整SQL，不要写入文件

## 典型场景

用户说："把实验号改成 162160 图上和 162159 图外，日期改成 0508 到 0513"

则需要：
- 识别 SQL 中所有旧实验号
- 替换为新的实验号（162160-0, 162160-dz, 162159-0, 162159-dz）
- 更新所有 CASE 的标签名称
- 更新所有 WHERE 的过滤条件
- 替换所有日期为 20260508 ~ 20260513