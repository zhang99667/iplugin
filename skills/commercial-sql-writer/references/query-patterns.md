# 商业广告 SQL 模板

模板用于快速生成结构，不代表字段一定齐全。落地前必须结合 `table-guide.md` 和 `metric-rules.md` 做字段确认和自查。

## 0. 商业大盘展点消转母版优先

多数商业需求不是从零写 SQL，而是在成熟的大盘展点消转 SQL 上做最小改写。优先保留这条主结构：

```text
outer group by 维度
  t1: asp_view 展点消
      event_day / searchid_decimal / ideaid / cmatch / exp_id / trans_type
      eshow / click / charge
  LEFT JOIN
  t2: 转化和目标成本
      ocpx_charge_hour 点击转化
      UNION ALL video_play_conv 视频/播放转化
      UNION ALL all_convert ROI/特殊转化价值
      group by search_id, idea_id
  ON t1.searchid_decimal = t2.search_id
 AND t1.ideaid = t2.idea_id
```

默认输出指标：

```sql
SUM(eshow) AS eshow,
SUM(click) AS click,
SUM(charge) AS charge,
SUM(CAST(convert_num AS INT)) AS total_convert_num,
SUM(target_charge) AS total_target_charge
```

改写原则：

- 改日期、实验号、`cmatch`、`event_type`、端、维度时，优先 patch 现有母版 SQL。
- 用户说“大盘”且上下文是 719 时，优先使用 `event_type = 'browser' AND cmatch = '719'`。
- 需要“覆盖部分/命中过某事件/命中过某物料”的展点消转时，不要另写孤立 SQL；把命中集合内联到 `t1` 展点消集合，或在 `t1` 前加 `hit_pv` 后再复用原 `t2`。
- 只有用户明确要求简化版、快速估算、单表趋势时，才使用下面的简化模板。

覆盖部分常见改法：

```sql
-- 保留原大盘 t1 的展点消字段和 charge 口径，只在 t1 内增加命中集合约束
FROM (
    SELECT
        event_day,
        searchid_decimal,
        ideaid,
        cmatch,
        trans_type,
        eshow,
        clk AS click,
        CASE
            WHEN (bid_type = '3' AND pricing_type = '1') OR bid_type = '2'
            THEN price / 1000 / 100
            ELSE clk * price / 100
        END AS charge
    FROM fc_nad.nativeads_feed_asp_view
    WHERE event_day BETWEEN '${start_day}' AND '${end_day}'
        AND event_type = '${event_type}'
        AND cmatch = '${cmatch}'
        -- 原实验过滤保留
        -- AND (ovl_exp LIKE '%${exp_id}-0%' OR ovl_exp LIKE '%${exp_id}-dz%')
) t1
INNER JOIN (
    SELECT DISTINCT
        event_day,
        search_id,
        idea_id
    FROM fc_nad.nativeads_ods_als_common
    WHERE event_day BETWEEN '${start_day}' AND '${end_day}'
        AND log_type IN (${log_type_list})
        -- AND page IN (${page_list})
        -- AND area IN (${area_list})
) hit
    ON t1.event_day = hit.event_day
    AND t1.searchid_decimal = hit.search_id
    AND t1.ideaid = hit.idea_id
-- 后续继续 LEFT JOIN 原 t2 转化目标成本
```

## 1. 展点消大盘

```sql
WITH base AS (
    SELECT
        event_day,
        cmatch,
        trans_type,
        wosid,
        SUM(CAST(eshow AS BIGINT)) AS eshow,
        SUM(CAST(clk AS BIGINT)) AS click,
        SUM(
            CASE
                WHEN (bid_type = '3' AND pricing_type = '1') OR bid_type = '2'
                THEN CAST(price AS DOUBLE) / 1000
                ELSE CAST(clk AS DOUBLE) * CAST(price AS DOUBLE)
            END
        ) / 100 AS charge
    FROM fc_nad.nativeads_feed_asp_view
    WHERE event_day BETWEEN '${start_day}' AND '${end_day}'
        AND event_type = '${event_type}'
        AND cmatch IN (${cmatch_list})
        -- AND wosid = '${wosid}'
    GROUP BY
        event_day,
        cmatch,
        trans_type,
        wosid
)
SELECT
    event_day,
    cmatch,
    trans_type,
    wosid,
    eshow,
    click,
    charge,
    CASE WHEN eshow > 0 THEN click / eshow ELSE 0 END AS ctr,
    CASE WHEN eshow > 0 THEN charge / eshow * 1000 ELSE 0 END AS ecpm
FROM base
ORDER BY event_day, cmatch, trans_type, wosid;
```

## 2. 带实验分组的展点消

```sql
WITH asp AS (
    SELECT
        event_day,
        CASE
            WHEN ovl_exp LIKE '%${exp_id}-0%' THEN 'exp'
            WHEN ovl_exp LIKE '%${exp_id}-dz%' THEN 'dz'
            ELSE 'other'
        END AS exp_group,
        cmatch,
        searchid_decimal,
        ideaid,
        trans_type,
        SUM(CAST(eshow AS BIGINT)) AS eshow,
        SUM(CAST(clk AS BIGINT)) AS click,
        SUM(
            CASE
                WHEN (bid_type = '3' AND pricing_type = '1') OR bid_type = '2'
                THEN CAST(price AS DOUBLE) / 1000
                ELSE CAST(clk AS DOUBLE) * CAST(price AS DOUBLE)
            END
        ) / 100 AS charge
    FROM fc_nad.nativeads_feed_asp_view
    WHERE event_day BETWEEN '${start_day}' AND '${end_day}'
        AND event_type = '${event_type}'
        AND cmatch IN (${cmatch_list})
        AND (
            ovl_exp LIKE '%${exp_id}-0%'
            OR ovl_exp LIKE '%${exp_id}-dz%'
        )
    GROUP BY
        event_day,
        CASE
            WHEN ovl_exp LIKE '%${exp_id}-0%' THEN 'exp'
            WHEN ovl_exp LIKE '%${exp_id}-dz%' THEN 'dz'
            ELSE 'other'
        END,
        cmatch,
        searchid_decimal,
        ideaid,
        trans_type
)
SELECT
    event_day,
    exp_group,
    cmatch,
    trans_type,
    SUM(eshow) AS eshow,
    SUM(click) AS click,
    SUM(charge) AS charge
FROM asp
GROUP BY event_day, exp_group, cmatch, trans_type
ORDER BY event_day, exp_group, cmatch, trans_type;
```

## 3. 展点消 join 转化

```sql
WITH asp AS (
    SELECT
        event_day,
        searchid_decimal,
        ideaid,
        cmatch,
        trans_type,
        SUM(CAST(eshow AS BIGINT)) AS eshow,
        SUM(CAST(clk AS BIGINT)) AS click,
        SUM(
            CASE
                WHEN (bid_type = '3' AND pricing_type = '1') OR bid_type = '2'
                THEN CAST(price AS DOUBLE) / 1000
                ELSE CAST(clk AS DOUBLE) * CAST(price AS DOUBLE)
            END
        ) / 100 AS charge
    FROM fc_nad.nativeads_feed_asp_view
    WHERE event_day BETWEEN '${start_day}' AND '${end_day}'
        AND event_type = '${event_type}'
        AND cmatch IN (${cmatch_list})
    GROUP BY event_day, searchid_decimal, ideaid, cmatch, trans_type
),
conv AS (
    SELECT
        event_day,
        search_id,
        idea_id,
        cmatch,
        SUM(CAST(convert_num AS BIGINT)) AS conv,
        SUM(CAST(ocpc_bid AS DOUBLE) * CAST(convert_num AS DOUBLE)) / 100 AS tcharge
    FROM fc_nad.nativeads_ocpx_charge_hour
    WHERE event_day BETWEEN '${start_day}' AND '${end_day}'
        AND cmatch IN (${cmatch_list})
        AND ocpc_level = 2
        AND convert_num IS NOT NULL
        AND convert_num != '0'
    GROUP BY event_day, search_id, idea_id, cmatch
)
SELECT
    a.event_day,
    a.cmatch,
    a.trans_type,
    SUM(a.eshow) AS eshow,
    SUM(a.click) AS click,
    SUM(a.charge) AS charge,
    SUM(COALESCE(c.conv, 0)) AS conv,
    SUM(COALESCE(c.tcharge, 0)) AS tcharge
FROM asp a
LEFT JOIN conv c
    ON a.searchid_decimal = c.search_id
    AND a.ideaid = c.idea_id
    AND a.event_day = c.event_day
GROUP BY a.event_day, a.cmatch, a.trans_type
ORDER BY a.event_day, a.cmatch, a.trans_type;
```

## 4. ALS 事件命中后回看展点消

适合半屏、优惠券、私信、预渲染、按钮点击等“先找命中 PV，再看展点消”的需求。

```sql
WITH hit_pv AS (
    SELECT
        event_day,
        search_id,
        idea_id,
        cmatch,
        MAX(page) AS page,
        MAX(area) AS area
    FROM fc_nad.nativeads_ods_als_common
    WHERE event_day BETWEEN '${start_day}' AND '${end_day}'
        AND log_type IN (${log_type_list})
        -- AND page IN (${page_list})
        -- AND product_id = '${product_id}'
    GROUP BY event_day, search_id, idea_id, cmatch
),
asp AS (
    SELECT
        event_day,
        searchid_decimal,
        ideaid,
        cmatch,
        SUM(CAST(eshow AS BIGINT)) AS eshow,
        SUM(CAST(clk AS BIGINT)) AS click,
        SUM(
            CASE
                WHEN (bid_type = '3' AND pricing_type = '1') OR bid_type = '2'
                THEN CAST(price AS DOUBLE) / 1000
                ELSE CAST(clk AS DOUBLE) * CAST(price AS DOUBLE)
            END
        ) / 100 AS charge
    FROM fc_nad.nativeads_feed_asp_view
    WHERE event_day BETWEEN '${start_day}' AND '${end_day}'
        AND event_type = '${event_type}'
        AND cmatch IN (${cmatch_list})
    GROUP BY event_day, searchid_decimal, ideaid, cmatch
)
SELECT
    h.event_day,
    h.cmatch,
    h.page,
    h.area,
    SUM(a.eshow) AS eshow,
    SUM(a.click) AS click,
    SUM(a.charge) AS charge
FROM hit_pv h
LEFT JOIN asp a
    ON h.search_id = a.searchid_decimal
    AND h.idea_id = a.ideaid
    AND h.event_day = a.event_day
GROUP BY h.event_day, h.cmatch, h.page, h.area
ORDER BY h.event_day, h.cmatch, h.page, h.area;
```

## 5. 按 search_id / idea_id 下钻

```sql
SELECT
    event_day,
    searchid_decimal,
    ideaid,
    cmatch,
    trans_type,
    wosid,
    mt_id,
    place_id,
    ovl_exp,
    CAST(eshow AS BIGINT) AS eshow,
    CAST(clk AS BIGINT) AS click,
    CASE
        WHEN (bid_type = '3' AND pricing_type = '1') OR bid_type = '2'
        THEN CAST(price AS DOUBLE) / 1000 / 100
        ELSE CAST(clk AS DOUBLE) * CAST(price AS DOUBLE) / 100
    END AS charge
FROM fc_nad.nativeads_feed_asp_view
WHERE event_day BETWEEN '${start_day}' AND '${end_day}'
    AND event_type = '${event_type}'
    AND searchid_decimal IN (${search_id_list})
ORDER BY event_day, searchid_decimal, ideaid;
```

下钻 SQL 不要过早聚合；优先保留能解释问题的字段。
