---
name: android-mock
version: 0.1.0
description: Android mock 自测与验收闭环助手。用于用户提供 Android mock 文档、scheme 文档、测试用例、mockserver 脚本、接口 mock 配置，或要求“帮我自测”“跑完用例”“验收链路”“补截图/录屏证据”“生成验收报告”时；覆盖真机 adb 执行、mockserver 请求核验、多链路分别验收、逐 case 证据留存、截图/录屏/logcat 采证、HTML/Markdown 验收结果归档。
tags: [android, mock, acceptance, testing, adb, logcat, evidence, html-report]
---

# Android Mock 自测验收

目标：把 Android mock 自测做成可追溯的验收闭环，而不是只抽样跑通主路径。

## 核心原则

- 以用户提供的 mock 方案、测试用例、技术文档、scheme 构造脚本、接口说明和实际包环境为准。
- mock 方案和验收结果分开：方案写“怎么测”，验收结果写“测了什么、结果是什么、证据在哪里”。
- 多条链路必须分别验收，例如宿主 App 链路、SDK 链路、内部入口、外部 scheme 入口；不要用一条链路的结果代替另一条链路。
- 每个 case 都要有状态：`通过`、`通过*`、`差异`、`失败`、`未测`。`未测` 必须说明原因。
- 每个结论都要有证据：mockserver 日志、设备截图、录屏、logcat、dumpsys、接口响应，或“没有收到请求”的观察窗口。
- 临时 mockserver、代理、dev server、logcat tail 等进程，结束前要停止，除非用户明确要求保留。

## 执行流程

1. 梳理输入。
   - 找到测试用例表、mockserver、scheme 生成方式、目标包名、入口协议、设备要求。
   - 提取所有链路和 case：请求方式、接口路径、query/body、mock 返回、预期拨号/跳转/toast/兜底/上报。
   - 如果文档和脚本不一致，记录差异；优先按实际可执行脚本或用户确认口径执行。
2. 准备环境。
   - 启动 mockserver，记录端口和 base URL。
   - 如 App 内访问本机回环地址，执行 `adb reverse tcp:<port> tcp:<port>`。
   - 执行 `adb devices` 确认真机在线。
   - 每个 case 前尽量清理残留状态：关闭拨号盘或目标 App、回到桌面、清空 logcat。
3. 逐 case 执行。
   - 一次只跑一个 case、一个链路。
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
- SDK 或桥接链路必须记录实际入口；如果外部 scheme 需要桥接到内部入口，要写清桥接关系。

## 常用命令

根据项目脚本优先使用本地封装。常见 adb 命令：

```bash
adb devices
adb reverse tcp:<port> tcp:<port>
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

复杂验收报告优先使用以下结构：

1. 文档抬头
2. 结论摘要
3. 链路 A 验收结果
4. 链路 B 验收结果
5. 差异、失败和未测项
6. 证据附录
7. 提交前清理
8. 证据来源

报告表格不要过密。多链路结果应分开写，每条链路单独成表。每个 case 行至少包含：

- case id / 名称
- 结果状态
- 实测行为
- 证据编号或证据路径
- 备注 / caveat

证据附录单独维护，表格里只引用证据编号，避免把截图、视频、长日志全部塞进 case 表格。

如果输出 HTML 报告且当前环境存在 `html-report` 能力，媒体证据优先使用它的标准结构：

- 图片：`<figure class="media-evidence" data-case="..." data-conclusion="...">` + `<img alt="...">` + `<figcaption class="media-caption">`。
- 录屏：同一个媒体证据块里放关键帧截图和 `<video controls preload="metadata">`，视频使用相对路径，不要 base64。
- 证据资源默认放在 HTML 同目录下的 `evidence_YYYYMMDD/`，并在 caption 里写清 case、结论和原始文件链接。

## 完成标准

不要在以下条件满足前宣布验收完成：

- 每条链路的每个 case 都有状态。
- 每个状态都有证据或明确阻塞原因。
- 证据路径存在，截图/录屏命名可追溯到 case。
- 报告中多链路结果分开呈现。
- mock 方案、验收结果、临时改动清理项分别呈现，不混在一张密集大表里。
- 临时日志、mock-only 代码、待回退改动已经列入提交前清理项。
- 临时服务已停止，或已说明仍在运行。
