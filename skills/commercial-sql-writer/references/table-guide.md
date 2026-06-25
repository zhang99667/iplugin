# 商业广告 SQL 表与字段指南

本文件用于在写 SQL 前做最小必要的 schema linking：先选相关表和字段，再生成 SQL。不要一次性加载所有表结构。

## 常用表

| 表 | 用途 | 关键字段 | 分区/过滤 |
| --- | --- | --- | --- |
| `fc_nad.nativeads_feed_asp_view` | 展点消主表，ASP 视角曝光、点击、消费和广告属性 | `event_day`, `event_type`, `cmatch`, `searchid_decimal`, `ideaid`, `eshow`, `clk`, `price`, `bid_type`, `pricing_type`, `trans_type`, `wosid`, `mt_id`, `place_id`, `ovl_exp`, `iad_ex` | 必带 `event_day`，尽量带 `event_type`；按场景补 `cmatch` |
| `fc_nad.nativeads_ods_als_common` | 客户端通用行为日志，适合页面事件、半屏、调起、下载漏斗、曝光/点击事件下钻 | `event_day`, `log_type`, `product_id`, `os_type`, `page`, `area`, `search_id`, `idea_id`, `cmatch`, `ovid_eid_list`, `eid_list`, `trans_type` | 必带 `event_day`，按事件带 `log_type` / `page` / `product_id` |
| `fc_nad.nativeads_ods_als_normal` | ALS normal 日志，适合曝光/点击、广告位、楼层、扩展字段排查 | `event_day`, `log_type`, `search_id`, `idea_id`, `cmatch`, `os_type`, `product_id`, `page_code`, `place_id`, `ovid_eid_list`, `da_ext*`, `daext*` | 必带 `event_day` 和 `log_type` |
| `fc_nad.nativeads_als_every_log` | 落地页性能日志，适合 `category_id = '1029'` 的落地页 URL、抵达率、预加载/预渲染状态、页面性能耗时分析 | `event_day`, `product_id`, `category_id`, `f1`-`f20`, `ef1`-`ef31`, `os_type` | 必带 `event_day` 和 `category_id = '1029'`；按端补 `os_type`，按广告类型补 `f1` |
| `fc_nad.nativeads_ocpx_charge_hour` | 点击转化、OCPX 转化、目标成本和出价信息 | `event_day`, `search_id`, `idea_id`, `cmatch`, `ovl_id`, `trans_type`, `convert_num`, `ocpc_bid`, `deep_ocpc_bid`, `deep_trans_type`, `is_ocpc_deep`, `convert_type_list`, `ocpc_level`, `cust_id` | 必带 `event_day`，转化口径常带 `ocpc_level = 2` |
| `fc_nad.nativeads_video_play_conv` | 视频/播放链路转化，常与点击转化合并 | `event_day`, `search_id`, `idea_id`, `cmatch`, `ovid_eid_list`, `trans_type`, `convert_num`, `ocpc_bid`, `deep_ocpc_bid`, `deep_trans_type`, `is_ocpc_deep`, `convert_type_list` | 必带 `event_day` 和业务 `cmatch` |
| `basedata.fc_advertisers` | 广告主基础信息、行业、客户实体、内部客户过滤 | `event_day`, `user_id`, `user_name`, `company`, `meg_trade_name_*`, `is_inner`, `custid`, `cust_name`, `father_id`, `father_name` | 按 `event_day` 取当日或最新分区 |
| `ubs_feed.feed_dwd_pub_log_hi` | Feed 用户行为明细，DAU、主 Feed、频道页、资源行为 | `event_day`, `event_action`, `appid`, `is_spam`, `page_type`, `r_type` | 主 Feed 标准过滤见下文 |
| `ubs_baiduapp.baiduapp_dwd_log_mix_hi` | 手百矩阵产品日志，适合 UBC/调起/矩阵行为分析 | 按具体需求查字段 | 必带日期分区和事件约束 |

## `nativeads_feed_asp_view` 使用要点

- `nativeads_feed_asp_view` 是多个 `nativeads_*_view` 的合并视图，用 `event_type` 区分来源流量，包括 `haokan`、`shoubai`、`page`、`tieba`、`browser`、`huichuan`、`bes`、`quanmin`。
- 表按 `eshow` 展开，常见情况下每条日志的 `eshow = 1`。需要广告数、PV 明细或对账时，不要把它误认为一条已经聚合好的记录。
- CPC 计费对应的 ASP 会按第一条 CPC 计费时间落盘。例如 1 点产生 ASP 检索、2 点发生 CPC 计费，这条 ASP 在 view 中可能落到 2 点分区。
- 如果要区分大字版、主版等产品形态，`asp_view` 不一定直接给出完整产品维度，常见做法是用 `search_id + cmatch + rank` 拼 ALS 日志，再从 ALS 取 `product_id`。
- `event_type` 和 `cmatch` 要配合使用：`event_type` 是分区和大流量范围，`cmatch` 是广告位/场景。只写 `cmatch` 不写 `event_type` 容易扩大扫描。

## 落地页性能日志 `nativeads_als_every_log`

当用户要分析“落地页性能”“落地页抵达率”“单个落地页 URL 抵达率”时，优先识别是否是 `category_id = '1029'` 的落地页性能日志。该日志的 `f*` 和 `ef*` 字段是位置字段，写 SQL 前先做字段映射。

常用过滤：

```sql
AND category_id = '1029'
AND product_id = '8'       -- 手百
AND f1 = 'ad'              -- 原生广告；开屏广告为 xuzhang
AND os_type = '2'          -- Android；iOS 为 1
```

`category_id = '1029'` 下原生广告常用 `f*` 字段：

| 字段 | 含义 |
| --- | --- |
| `f1` | 广告类型：`ad` 为原生广告，`xuzhang` 为开屏广告 |
| `f2` | `lp_real_url`，落地页真实地址 |
| `f3` | `place_id` |
| `f4` | `plan_id` |
| `f5` | `unit_id` |
| `f6` | `idea_id` |
| `f7` | `cmatch` |
| `f8` | `search_id` |
| `f9` | `eid_list` |
| `f10` | `user_id` |
| `f11` | `cpid` |
| `f12` | `mt` |
| `f13` | `rank` |

落地页性能常用 `ef*` 字段：

| 字段 | 含义 |
| --- | --- |
| `ef1` | 预加载/预渲染字段：预加载为 1，串行预渲染 3，并行计费预渲染 4，预渲染新方案 5 |
| `ef2` | `clickTime`，用户点击广告时间，毫秒 |
| `ef3` | `isbrowser`，抵达时间；第一个 200 页面请求 `loadFinish` 时间，毫秒。iOS 为 `loadFinish`，Android 为 `fsp` |
| `ef4` | `aderrorcode`，加载失败错误码 |
| `ef5` | 页面停留时间，毫秒 |
| `ef6` | `navigationstart`，毫秒 |
| `ef7` | `domfirstscreenpaint`，仅 Android 有，毫秒 |
| `ef8` | `domcomplete`，毫秒 |
| `ef9` | `performanceTiming` JSON |
| `ef10` | `Entries` JSON |
| `ef11` | NA Activity 生命周期时间 JSON |
| `ef12` | 是否弱网：1 弱网，0 非弱网 |
| `ef14` | 预渲染状态。Android 11-17 分别表示曝光、满足条件、发起、可用、失败、销毁、未使用 webview 被顶掉；iOS 为新方案成功/失败状态 |
| `ef15` | 业务打点 JSON |
| `ef16` | webview 预创建：1 表示预创建 |
| `ef17` | 二跳打点：1 有二跳，0 无二跳 |
| `ef18` | 特定字符串拦截打点 JSON |

抵达率常见口径：

```sql
arrival = CAST(ef3 AS double) > 10000
      AND CAST(ef2 AS double) > 10000
      AND CAST(ef3 AS double) >= CAST(ef2 AS double)
      AND CAST(ef3 AS double) - CAST(ef2 AS double) < 30000

arrival_rate = arrival / click
```

注意：
- `f7` 才是 `cmatch`；如果用户说“原生 cmatch=669”，需要补 `AND f7 = '669'`，不能误用 `category_id`。
- `f2` 是落地页 URL，不是拼接键；`search_id + idea_id` 对应 `f8 + f6`。
- iOS 可能因后台切前台重复打点，按文档建议用 `cuid + clickTime` 去重；Android 和大盘临时排查也要先确认是否需要按 `f8, f6` 或 `cuid, ef2` 去重。
- 原始日志直接 `COUNT(*)` 没有去重，结果可能偏大；分享 SQL 时必须说明是否去重。

## Join 规则

| 场景 | 正确 join | 注意 |
| --- | --- | --- |
| `asp_view` join ALS / OCPX / AFD | `asp_view.searchid_decimal = other.search_id` | `asp_view.searchid` 是 16 进制，不要直接 join |
| 创意维度 join | `asp_view.ideaid = other.idea_id` | `asp_view` 字段名是 `ideaid`，其他表常是 `idea_id` |
| 同日行为 join | 同时加 `event_day` | 避免跨天误 join |
| 只看 PV 是否命中事件 | 行为表先按 `event_day, search_id, idea_id` 去重 | 避免一条 PV 多事件放大展点消 |

## 常见枚举

### `event_type`

| 值 | 含义 |
| --- | --- |
| `shoubai` | 手百 |
| `haokan` | 好看 |
| `page` | 落地页 |
| `tieba` | 贴吧 |
| `browser` | 浏览器 |
| `huichuan` | 汇川 |
| `bes` | 百青藤 |
| `quanmin` | 全民小视频 |

### `wosid` / `os_type`

| 值 | 含义 |
| --- | --- |
| `1` | iOS |
| `2` | Android |
| `5` | HarmonyOS |

### 业务术语映射

| 术语 | 常用 SQL 条件 |
| --- | --- |
| 手百 | `event_type = 'shoubai'` |
| 好看 | `event_type = 'haokan'` |
| 安卓 | `wosid = '2'` 或 `os_type = '2'` |
| iOS | `wosid = '1'` 或 `os_type = '1'` |
| 鸿蒙 | `wosid = '5'` |
| 短小融合 / 719 | `event_type = 'browser' AND cmatch = '719'` |
| 图上 / 545 | 常见 `event_type = 'shoubai' AND cmatch = '545'` |
| 展点消 | `eshow`, `clk`, `charge` |

## 高频 `cmatch` 与 `event_type`

| cmatch | 常见场景 | 绑定/常用 `event_type` |
| --- | --- | --- |
| `719` | 短小融合、浏览器场景、很多商业大盘默认口径 | `browser` |
| `545` | 手百信息流图上/图外常见口径 | `shoubai` |

写 SQL 时不要只替 `cmatch` 忘记替 `event_type`。用户说“大盘”且上下文是 719 时，优先按 `event_type = 'browser' AND cmatch = '719'` 处理；除非用户明确指定其他流量。

## Feed 标准过滤

主 Feed 用户行为常用过滤：

```sql
AND event_action = 'display_list'
AND appid = 1
AND is_spam = 0
AND page_type = 0
```

说明：
- 主 Feed / 推荐频道通常是 `page_type = 0`。
- Feed 列表页通常可包含 `page_type IN (0, 3)`。
- 广告资源常用 `r_type = 'ad1'` 识别。

## 实验字段

| 表/场景 | 常用实验字段 | 分隔/匹配 |
| --- | --- | --- |
| `nativeads_feed_asp_view` | `ovl_exp` | 常见 `LIKE '%123456-0%'` / `LIKE '%123456-dz%'` |
| `nativeads_ocpx_charge_hour` | `ovl_id` | 常见 `LIKE` 或 `_` 分隔 |
| `nativeads_ods_als_common` / `normal` | `ovid_eid_list`, `eid_list` | 常见 `#` 分隔 |
| 视频转化 | `ovid_eid_list`, `ad_ovlexp_id_list_str` | 需结合具体字段含义 |

不要默认所有表的实验字段相同；生成跨表 SQL 时要分别过滤对应字段。
