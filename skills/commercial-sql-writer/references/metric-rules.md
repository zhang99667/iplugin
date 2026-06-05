# 商业广告指标口径

本文件用于生成或检查商业 SQL 中的指标口径。写 SQL 前先明确用户要的是曝光/点击/消费、转化、目标成本、漏斗，还是排查型明细。

## 展点消

基础指标：

```sql
SUM(CAST(eshow AS BIGINT)) AS eshow,
SUM(CAST(clk AS BIGINT)) AS click
```

`nativeads_feed_asp_view` 标准消费口径：

```sql
SUM(
    CASE
        WHEN (bid_type = '3' AND pricing_type = '1') OR bid_type = '2'
        THEN CAST(price AS DOUBLE) / 1000
        ELSE CAST(clk AS DOUBLE) * CAST(price AS DOUBLE)
    END
) / 100 AS charge
```

注意：
- `price` 在 `asp_view` 中常按分计，最终 `/100` 转元。
- oCPC/CPM 分支先按千次价格 `/1000`。
- 字段多数是 STRING，聚合和比较时显式 `CAST` 更稳。
- `asp_view` 按 `eshow` 展开时，历史文档里也常见按原始计费单位直接换算：`bid_type = '2'` 或 `bid_type = '3' AND pricing_type = '1'` 的 CPM-like 记录用 `price / 100000` 转元，其他 CPC 记录用 `price / 100` 转元。若沿用现有大盘 SQL，使用 `clk * price / 100` 可以避免非点击 CPC 曝光被误计费。
- CPC 计费记录可能按计费发生时间落盘，不一定等同检索发生小时；做小时级对账时要特别说明口径。

直接按原始计费单位转元的写法：

```sql
SUM(
    CASE
        WHEN bid_type = '2' OR (bid_type = '3' AND pricing_type = '1')
        THEN CAST(price AS DOUBLE) / 100000
        ELSE CAST(price AS DOUBLE) / 100
    END
) AS charge
```

使用这类写法时，通常还要结合 `price > 0` 或确认输入记录已经是计费记录；否则优先使用上面的标准大盘口径。

## CTR / ECPM

```sql
CASE
    WHEN SUM(CAST(eshow AS DOUBLE)) > 0
    THEN SUM(CAST(clk AS DOUBLE)) / SUM(CAST(eshow AS DOUBLE))
    ELSE 0
END AS ctr
```

```sql
CASE
    WHEN SUM(CAST(eshow AS DOUBLE)) > 0
    THEN SUM(charge) / SUM(CAST(eshow AS DOUBLE)) * 1000
    ELSE 0
END AS ecpm
```

如果同层 SELECT 不能复用别名，先在 CTE 中产出 `eshow`、`click`、`charge`，外层再算比例。

## 转化数

常见来源：
- 点击转化：`fc_nad.nativeads_ocpx_charge_hour`
- 视频/播放链路转化：`fc_nad.nativeads_video_play_conv`
- 全量转化明细：`nativeads_ods_ocpc_all_convert` / `nativeads_feed_ocpc_all_convert`

基础过滤：

```sql
convert_num IS NOT NULL
AND convert_num != '0'
```

常见 OCPX 过滤：

```sql
ocpc_level = 2
```

## 浅转 / 深转合并

常见逻辑：

```sql
CASE
    WHEN is_ocpc_deep = 1 AND deep_trans_type NOT IN ('28', '29')
    THEN IF(
        convert_num > 0
        AND array_contains(split(convert_type_list, '\002'), deep_trans_type),
        convert_num,
        0
    )
    ELSE convert_num
END AS merge_convert_num
```

视频转化表里 `convert_type_list` 常见 `#` 分隔；点击转化表里常见 `\002` 分隔。不要把两个分隔符混用。

## 目标成本 `tcharge`

常见目标成本：

```sql
SUM(CAST(ocpc_bid AS DOUBLE) * CAST(convert_num AS DOUBLE)) / 100 AS tcharge
```

深转合并目标成本：

```sql
SUM(
    CASE
        WHEN is_ocpc_deep = 1 AND deep_trans_type NOT IN ('28', '29')
        THEN CAST(deep_ocpc_bid AS DOUBLE) * CAST(deep_convert_num AS DOUBLE)
        ELSE CAST(ocpc_bid AS DOUBLE) * CAST(convert_num AS DOUBLE)
    END
) / 100 AS tcharge
```

注意：
- `nativeads_ocpx_charge_hour.price` 的单位和 `asp_view.price` 不同；不要复用消费公式。
- 部分 `trans_type` 不应计目标成本，历史 SQL 中常对 `14, 80, 81, 82, 83, 84, 85, 86, 87, 88, 90, 118` 做特殊处理。是否需要排除要按需求确认。

## 下载漏斗

ALS 下载类常见 `log_type`：

| log_type | 含义 |
| --- | --- |
| `701` | 开始下载 |
| `702` | 暂停下载 |
| `703` | 继续下载 |
| `704` | 下载完成/立即安装 |
| `706` | 打开应用 / deeplink |
| `708` | 重新下载 |
| `709` | 下载失败 |
| `710` | App 安装 |
| `721` | App 激活 |

漏斗模式：

```sql
MAX(IF(log_type = 701, 1, 0)) AS start_download,
MAX(IF(log_type = 704, 1, 0)) AS finish_download,
MAX(IF(log_type = 710, 1, 0)) AS install_app,
MAX(IF(log_type = 721, 1, 0)) AS active_app
```

按 `event_day, search_id, idea_id` 聚合，通常用 `HAVING MAX(IF(log_type = 701, 1, 0)) = 1` 约束漏斗起点。

## App 嗅探

`iad_ex` 常见格式为 `"[num1,num2,...]"`。先判断有效标识，再判断 app 位：

```sql
CAST(split(regexp_replace(iad_ex, '\\[|\\]', ''), ',')[0] AS BIGINT) & 1 <> 0
```

common 组第 N 个 app：

```sql
CAST(split(regexp_replace(iad_ex, '\\[|\\]', ''), ',')[0] AS BIGINT)
    & CAST(pow(2, N + 1) AS BIGINT) <> 0
```

group2 第 N 个 app：

```sql
CAST(split(regexp_replace(iad_ex, '\\[|\\]', ''), ',')[1] AS BIGINT)
    & CAST(pow(2, N) AS BIGINT) <> 0
```

注意 common 组第 0 位是有效标识，app 从第 1 位开始。
