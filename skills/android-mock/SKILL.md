---
name: android-mock
version: 0.1.2
description: Android mock 自测与验收闭环助手。用于用户提供 Android mock 文档、scheme 文档、测试用例、mockserver 脚本、接口 mock 配置，或要求“帮我自测”“跑完用例”“验收链路”“补截图/录屏证据”“生成验收报告”时；覆盖真机 adb 执行、mockserver 请求核验、多端/多模块/多链路完整验收、逐 case 证据留存、截图/录屏/logcat 采证，并强制使用 html-report 产出 HTML 验收报告。
tags: [android, mock, acceptance, testing, adb, logcat, evidence, html-report]
---

# Android Mock 自测验收

目标：把 Android mock 自测做成可追溯的验收闭环，而不是只抽样跑通主路径。

## 核心原则

- 以用户提供的 mock 方案、测试用例、技术文档、scheme 构造脚本、接口说明和实际包环境为准。
- mock 方案和验收结果分开：方案写“怎么测”，验收结果写“测了什么、结果是什么、证据在哪里”。
- 多条链路必须分别验收，例如宿主 App 链路、SDK 链路、内部入口、外部 scheme 入口；不要用一条链路的结果代替另一条链路。
- 多端、多模块或多入口复用同一测试用例时，也要按“端 / 模块 / 链路 / 入口 × case”展开逐项执行；不能因为 case 名相同就合并、抽样或跳过。
- 每个 case 都要有状态：`通过`、`通过*`、`差异`、`失败`、`未测`。`未测` 必须说明原因。
- 每个结论都要有证据：mockserver 日志、设备截图、录屏、logcat、dumpsys、接口响应，或“没有收到请求”的观察窗口。
- 验收报告必须新增或明确版本化输出；目标目录已有报告时，不要覆盖旧报告，除非用户明确要求替换。
- 临时 mockserver、代理、dev server、logcat tail 等进程，结束前要停止，除非用户明确要求保留。

## 执行流程

1. 梳理输入。
   - 找到测试用例表、mockserver、scheme 生成方式、目标包名、入口协议、设备要求。
   - 提取所有链路和 case：请求方式、接口路径、query/body、mock 返回、预期拨号/跳转/toast/兜底/上报。
   - 建立执行矩阵：把端、包、模块、链路、入口、case、mock case、预期和证据要求拆成独立行；相同 case 出现在多个端/模块/链路时，每一行都必须执行和记录。
   - 如果文档和脚本不一致，记录差异；优先按实际可执行脚本或用户确认口径执行。
2. 准备环境。
   - 启动 mockserver，记录端口和 base URL。
   - 如 App 内访问本机回环地址，执行 `adb reverse tcp:<port> tcp:<port>`。
   - 执行 `adb devices` 确认真机在线。
   - 验证端上到 mockserver 的通路时，优先用设备 shell 非 UI 命令，不要为了 healthz 先打开浏览器：
     - 首选：`adb shell toybox wget -q -O - http://127.0.0.1:<port>/healthz`
     - 如果设备 toybox 不带 wget，依次尝试 `adb shell curl -sS http://127.0.0.1:<port>/healthz`、`adb shell busybox wget -q -O - http://127.0.0.1:<port>/healthz`。
     - 只有设备 shell 没有可用 HTTP 工具时，才用 `adb shell am start -a android.intent.action.VIEW -d 'http://127.0.0.1:<port>/healthz'` 作为降级方案。
   - 保存通路验证证据：命令输出和 mockserver 的 `/healthz` 请求日志。
   - 每个 case 前尽量清理残留状态：关闭拨号盘或目标 App、回到桌面、清空 logcat。
3. 逐 case 执行。
   - 一次只跑执行矩阵中的一行：一个端/模块/链路/入口 + 一个 case。
   - 不要跳过矩阵行；如果时间、设备或包环境不足以全量执行，先向用户说明剩余矩阵和阻塞，不要自行把某条链路或模块标为“同上”。
   - 跑完立即采集 mockserver 输出、设备前台状态、关键 logcat。
   - 涉及视觉结果时截图或录屏。
   - 预期“不请求”的 case，要保留该时间窗口内 mockserver 没有新增请求的证据。
4. 判定状态。
   - `通过`：接口请求和设备表现都符合预期。
   - `通过*`：主行为符合预期，但 toast、设备策略、单个变体或视觉瞬态需要 caveat。
   - `差异`：当前包实测和文档预期不同，且差异可复现、有证据。
   - `失败`：预期主行为未发生，且没有合理 caveat。
   - `未测`：没有执行；必须写清阻塞原因、缺少条件或延后变体。

## 采证规范

- 稳定 UI 状态用截图：拨号盘号码、停留页面、未拉起拨号盘、错误页。
- toast、loading、短暂弹层用短录屏或连续截图；单张终帧截图只能证明最终状态。
- 请求成功要保存 mockserver 命中日志；请求失败要保存 HTTP 状态、错误日志或超时日志。
- 预期无请求时，保存观察窗口内 mockserver 无新增请求的日志片段。
- 证据文件放到日期目录，例如 `evidence_YYYYMMDD/`。
- 文件名包含链路、case、证据类型，例如 `sdk_tc06_final_YYYYMMDD.png`、`host_tc05_toast_YYYYMMDD.mp4`。
- 验收报告中每个 case 的结论下方必须直接放可见或可点证据：截图预览、录屏预览、mock/logcat/dumpsys 超链接至少一种；toast、loading、短暂弹层等时序证据优先放录屏和关键帧截图。
- SDK 或桥接链路必须记录实际入口；如果外部 scheme 需要桥接到内部入口，要写清桥接关系。

## 常用命令

根据项目脚本优先使用本地封装。常见 adb 命令：

```bash
adb devices
adb reverse tcp:<port> tcp:<port>
adb shell toybox wget -q -O - http://127.0.0.1:<port>/healthz
adb shell curl -sS http://127.0.0.1:<port>/healthz
adb shell input keyevent HOME
adb shell logcat -c
adb shell dumpsys activity activities
adb shell screencap -p /sdcard/<case>.png
adb shell screenrecord --time-limit 8 /sdcard/<case>.mp4
adb pull /sdcard/<case>.png evidence_YYYYMMDD/<case>.png
adb pull /sdcard/<case>.mp4 evidence_YYYYMMDD/<case>.mp4
```

logcat 只截取和当前 case 相关的短片段：

```bash
adb shell logcat -d -v time | rg -i "uri=tel|Toast|NotificationService|REQUEST_FAILED|ActivityTaskManager|UBC|error|scheme"
```

## 验收报告

HTML 验收报告必须使用 `html-report` skill 生成，不要手写自定义 HTML 模板。流程要求：

- 先按 `html-report` skill 读取并遵守其内容规则、视觉规则、CSS 模板和校验要求。
- 输出 HTML 时使用 `html-report` 的正式文档抬头、摘要、链路分表、逐 case 证据块、媒体证据结构、证据来源和清理确认。
- 写入前检查目标目录已有验收报告；如果同名文件存在，生成带轮次、日期或时间戳的新文件名，并在报告抬头说明“新增报告，未覆盖历史报告”。
- 完成前运行 `html-report/scripts/check_html_report.py <html-file>`；校验失败必须修复后重跑，直到通过。
- 只有用户明确要求不要 HTML 或只要 Markdown 时，才输出 Markdown 验收结果。

复杂验收报告优先使用以下结构：

1. 文档抬头
2. 结论摘要
3. 链路 A 验收结果
4. 链路 B 验收结果
5. 差异、失败和未测项
6. 逐 case 证据块
7. 提交前清理
8. 证据来源

报告表格不要过密。多链路结果应分开写，每条链路单独成表或逐 case 卡片。每个 case 行至少包含：

- case id / 名称
- 结果状态
- 实测行为
- 证据编号或证据路径
- 备注 / caveat

**优先使用逐 case 卡片（而非纯汇总表格 + 超链接）**：每个 case 用独立卡片 `.case-card`，卡片内直接内嵌截图/录屏预览（`<figure class="media-evidence">`），读者不需要跳转就能看到证据。纯表格 + 超链接只作为密集总览的补充，不能替代卡片内嵌图片。

证据附录可以保留用于汇总原始文件，但不能替代 case 下证据。每个 case 必须在对应卡片或小节的紧邻位置内嵌截图/录屏预览（直接显示图片，不是仅放超链接）；toast、loading 等时序证据优先放录屏和关键帧截图。超链接只用于辅助指向完整 mock 日志或 logcat 原始文件，不能作为主证据形式。

HTML 报告中的媒体证据使用 `html-report` 标准结构：

- 图片：`<figure class="media-evidence" data-case="..." data-conclusion="...">` + `<img alt="...">` + `<figcaption class="media-caption">`。
- 录屏：同一个媒体证据块里放关键帧截图和 `<video controls preload="metadata">`，视频使用相对路径，不要 base64。
- 证据资源默认放在 HTML 同目录下的 `evidence_YYYYMMDD/`，并在 caption 里写清 case、结论和原始文件链接。
- 如果截图或录屏不适合内嵌预览，仍要在 case 下放清晰的相对路径超链接，链接文本写明证据类型和结论，不要让读者去附录反查。

## 完成标准

不要在以下条件满足前宣布验收完成：

- 每条链路的每个 case 都有状态。
- 执行矩阵中的每一行都有状态；多端、多模块或多入口的相同 case 也要分别有结果和证据，不能用其他链路的结论代替。
- 每个状态都有证据或明确阻塞原因。
- 证据路径存在，截图/录屏命名可追溯到 case。
- 报告每个 case 下都有截图、录屏或日志/原始文件超链接作为直接证据；仅有总表或仅有证据附录不算完成。
- 报告中多链路结果分开呈现。
- HTML 验收报告由 `html-report` 生成，并通过 `check_html_report.py`。
- HTML 验收报告没有覆盖历史报告；如必须覆盖，已有用户明确指令或已先备份。
- mock 方案、验收结果、临时改动清理项分别呈现，不混在一张密集大表里。
- 临时日志、mock-only 代码、待回退改动已经列入提交前清理项。
- 临时服务已停止，或已说明仍在运行。
