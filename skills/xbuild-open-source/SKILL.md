---
name: xbuild-open-source
version: 0.1.1
tags: [baidu, easybox, xbuild, mgit, android, syncSource, source-mode]
description: 百度 EasyBox/xbuild 源码模式自动补开助手。当用户要求“开源码”“打开仓库”“打开某个模块源码模式”“把仓库加到 modules-local*.gradle/modules-overlay*.gradle”“syncSource true”，需要从崩溃栈/类名/包名/模块名/远端仓库反查 xbuild 模块，或在代码阅读、调用链追踪、问题排查、代码修改中发现目标源码未出现在 repos、只有 Maven/AAR/符号线索时触发，即使用户没有明确说“开源码”。用于定位 xbuild/modules/default 映射、检查源码模式和本地仓状态、唯一命中时自动最小修改 local 配置并精确同步缺失仓，然后继续原任务。
---

# Xbuild Open Source

用于百度 App Android / EasyBox / xbuild 多仓工程里，把 Maven 依赖切成本地源码模式。优先做只读定位，再对唯一目标自动补齐个人源码模式和缺失仓；不要在“尚未同步”处停止原代码任务。

## Workflow

1. 先读 `references/xbuild-source-mode.md`。
2. 判断用户目标：只定位映射、显式打开源码，还是在其他代码任务中隐式发现源码缺失。后两种都进入补开闭环，不要求用户再说一次“开源码”。
3. 用 `rg` 在 `repos`、当前工程和 `xbuild/modules/default` 中反查模块路径、`absoluteRepo` 与本地目录，不能靠仓库名猜。
4. 检查目标模块在 local/overlay 中的 `syncSource` 状态，以及映射对应的 `repos/<层级>/<仓库>` 是否存在。
5. 只有一个高置信映射时按状态处理：
   - 源码仓已存在：直接继续原代码任务；用户显式要求打开构建源码模式时，再最小补 `syncSource true`。
   - 源码仓不存在，且 `syncSource` 未配置或为 `false`：最小补 `syncSource true`，再只同步该目标仓。
   - `syncSource true` 已存在但源码仓不存在：不重复编辑配置，只同步该目标仓。
6. 选择覆盖文件：
   - 用户指定 `xbuild/modules/local/*.gradle` 时，直接在该文件做最小修改。
   - 开发分支上车/CI 共用时优先 `xbuild/modules/overlay/*.gradle`。
   - master 合入、个人本地调试或隐式发现源码缺失时优先 `xbuild/modules/local/*.gradle`；不要为隐式补开修改公共 overlay。
7. 只新增或更新目标模块的 `syncSource true`，保留无关配置；修改后读回目标段落。
8. 源码仓缺失时做 MGIT 预检，通过 `mgit -al` / `mgit info` 验证精确仓库名，然后执行 `mgit sync -c <exact-repo>`。这是“打开源码”或完成当前代码任务的一部分，无需二次确认。
9. 同步后验证目标目录存在，继续用户原本的代码阅读、排障或修改任务；汇报模块路径、远端仓库、覆盖文件和同步结果。

## Safety

- 不修改 `xbuild/modules/default/*.gradle`，除非用户明确要求改基础映射。
- 自动同步仅限 default 映射唯一、MGIT 仓库名已验证且本地目录缺失的目标仓，只允许 `mgit sync -c <exact-repo>`；不自动执行全量 `mgit sync`、`mgit sync -n`、pull 或更新已有仓。
- `git checkout`、切分支、全量同步、pull、reset、清理或删除操作仍须说明影响范围并等待用户确认。
- 如果 MGIT 预检失败，说明依赖问题，不要继续跑 MGIT。
- 如果同一个符号可能来自多个仓，先列候选和证据，让用户确认。
- 如果精确同步失败，保留已经完成的最小配置，报告失败命令和原因，不要改用更大范围的同步命令兜底。
