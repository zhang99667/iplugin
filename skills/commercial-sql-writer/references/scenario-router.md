# 商业 SQL 场景路由

根据用户自然语言选择表、字段和模板。没有把握时先说明假设，不要硬猜字段。

## 大盘 / 展点消转

信号词：大盘、展点消转、展点消、曝光、点击、消费、转化、目标成本、CTR、ECPM、按天趋势。

优先：
- 主表：`fc_nad.nativeads_feed_asp_view`
- 母版：`query-patterns.md` 的“商业大盘展点消转母版优先”
- 必问/必推断：日期、`event_type`、`cmatch`、端、维度

注意：
- 绝大多数商业大盘 SQL 都围绕 `t1` 展点消和 `t2` 转化/目标成本展开；不要轻易完全重写成另一套结构。
- 用户说“大盘”且上下文没有额外说明时，通常不是只要展点消，而是要 `eshow/click/charge/convert_num/target_charge`。
- 上下文为 719 时，默认绑定 `event_type = 'browser' AND cmatch = '719'`。

## 实验效果

信号词：实验组、对照组、dz、exp、ovl、eid、灰度、命中实验用户。

优先：
- 展点消实验字段：`ovl_exp`
- OCPX 转化实验字段：`ovl_id`
- ALS 行为实验字段：`ovid_eid_list` / `eid_list`
- 模板：带实验分组的展点消；若要转化，再 join 转化

注意：
- 同一需求跨多张表时，实验过滤字段往往不同。
- 只做实验号替换时转给 `sql-exp-replace`。

## 转化 / 目标成本

信号词：转化、浅转、深转、目标成本、tcharge、conv、ROI、oCPC。

优先：
- 点击转化：`fc_nad.nativeads_ocpx_charge_hour`
- 视频/播放转化：`fc_nad.nativeads_video_play_conv`
- 复杂全量转化：all_convert 相关表
- 规则：读 `metric-rules.md`

注意：
- 明确是否使用深转逻辑。
- 点击转化和视频转化合并时要避免重复计算。
- `convert_type_list` 分隔符在不同表中可能不同。

## 半屏 / WebPanel

信号词：半屏、webpanel、pop web panel、页面曝光、半屏统一。

优先：
- 命中 PV：`fc_nad.nativeads_ods_als_common`
- 回看展点消：join `fc_nad.nativeads_feed_asp_view`
- 模板：`query-patterns.md` 的“ALS 事件命中后回看展点消”

常见条件：
- 半屏/覆盖部分的展点消转，一般是在大盘展点消转母版上加命中集合，而不是另写一套孤立 SQL。
- `log_type` 需要按事件确认，历史半屏曝光常见 `103`
- `page` 可能是 `NAD_POP_WEB_PANEL`、`NAVIDEO_POP_WEB_PANEL` 等
- `product_id` 和 `event_type` 需要结合端和场景确认

## 优惠券 / 图上图外

信号词：优惠券、图上、图外、FREE_SHOW、mount_tag、物料、广告主覆盖。

优先：
- 展点消：`nativeads_feed_asp_view`
- 行为命中：`nativeads_ods_als_common`
- 物料/样式：`mt_id`、JSON 字段、`page`、`area`

注意：
- 图上/图外往往是业务口径，不一定只靠一个字段；先找历史 SQL 或让用户确认识别条件。
- 如果需求是“覆盖部分/命中过某物料/命中过某事件的展点消转”，优先把命中条件内联到大盘 `t1` 展点消集合，再复用原 `t2` 转化目标成本逻辑。
- 如果使用 JSON 字段，保留原 SQL 的解析方式，少做重写。

## 私信 / 调起 / Deeplink

信号词：私信、打开应用、deeplink、调起、openbtn、小程序调起。

优先：
- 行为日志：ALS common / normal 或矩阵日志
- 展点消回看：按 `search_id` + `idea_id` join asp

注意：
- 先明确用户要“调起次数”还是“调起 PV 对应展点消”。
- `click_area`、`area`、`page`、`log_type` 通常比表名更关键。

## 下载漏斗

信号词：下载、安装、激活、失败率、下载完成率、漏斗。

优先：
- 表：`fc_nad.nativeads_ods_als_common`
- 规则：`metric-rules.md` 的下载漏斗
- 分组：`event_day, search_id, idea_id`

注意：
- 先确认漏斗起点，默认可用 `701` 开始下载。
- 如果还要消费/转化，需要再 join asp 或 OCPX。

## 预渲染 / 成功率

信号词：预渲染、成功率、失败、耗时、性能。

优先：
- 先定位行为日志表和 `log_type` / `page` / `area`
- 指标通常是 `SUM(success) / SUM(total)` 或按事件状态聚合

注意：
- 预渲染成功/失败字段经常是扩展字段，不能凭空造字段。
- 若用户提供历史 SQL，优先保持其中的字段解析逻辑。

## 落地页性能 / 抵达率

信号词：落地页性能、落地页抵达率、抵达率、落地页 URL、单个落地页地址、`lp_real_url`、`isbrowser`、`clickTime`。

优先：
- 表：`fc_nad.nativeads_als_every_log`
- 字段映射：读 `table-guide.md` 的“落地页性能日志 `nativeads_als_every_log`”
- 常见过滤：`category_id = '1029'`、`product_id = '8'`、`f1 = 'ad'`、`os_type`、`f7` 作为 `cmatch`、`f2` 作为落地页 URL

常见指标：
- 点击量：未去重时 `COUNT(*)`；需要去重时按用户口径使用 `COUNT(DISTINCT ...)`
- 抵达量：`ef3` 和 `ef2` 合法，且 `ef3 - ef2` 在阈值内，常见阈值为 30000ms
- 抵达率：`arrival / click`，要处理分母为 0

注意：
- 用户说 `cmatch=669` 时应过滤 `f7 = '669'`，不是 `category_id = '1029'`。
- `f2` 是 URL；`search_id + idea_id` 对应 `f8 + f6`。
- 默认明确说明“未去重可能偏大”；iOS 抵达日志尤其注意按 `cuid + ef2(clickTime)` 去重。
- 抵达时间差建议加 `CAST(ef3 AS double) >= CAST(ef2 AS double)`，避免异常负差被算作抵达。

## 问题排查 / 下钻

信号词：by userid、by search_id、下钻、排查、命中用户、ideaid、host、502。

优先：
- 降低聚合层级，保留明细字段。
- 从命中 PV 或命中用户开始，再逐层 join 展点消/转化。
- 模板：`query-patterns.md` 的“按 search_id / idea_id 下钻”

注意：
- 排查 SQL 可以牺牲汇总美观，优先保留解释问题的字段。
- 大查询先限制日期、用户、search_id 或样本量。
