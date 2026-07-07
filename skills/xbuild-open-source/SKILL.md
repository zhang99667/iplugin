---
name: xbuild-open-source
version: 0.1.0
tags: [baidu, easybox, xbuild, mgit, android, syncSource, source-mode]
description: 百度 EasyBox/xbuild 源码模式打开助手。当用户要求“开源码”“打开仓库”“打开某个模块源码模式”“把仓库加到 modules-local*.gradle/modules-overlay*.gradle”“syncSource true”，或需要从崩溃栈/类名/包名/模块名/远端仓库反查 xbuild 模块并启用本地源码构建时触发。用于定位 xbuild/modules/default 映射、选择 local 或 overlay 覆盖文件、最小修改 syncSource，并在需要时指导 MGIT 同步源码仓。
---

# Xbuild Open Source

用于百度 App Android / EasyBox / xbuild 多仓工程里，把 Maven 依赖切成本地源码模式。优先做只读定位，再做最小配置修改；涉及同步、拉仓、切分支、清理等写操作时必须先确认影响范围。

## Workflow

1. 先读 `references/xbuild-source-mode.md`。
2. 判断用户目标：只定位要开哪个仓，还是已经指定覆盖文件并要求直接打开。
3. 用 `rg` 在 `xbuild/modules/default` 中反查模块路径，不能靠仓库名猜。
4. 选择覆盖文件：
   - 用户指定 `xbuild/modules/local/*.gradle` 时，直接在该文件做最小修改。
   - 开发分支上车/CI 共用时优先 `xbuild/modules/overlay/*.gradle`。
   - master 合入或个人本地调试时优先 `xbuild/modules/local/*.gradle`。
5. 只新增或更新目标模块的 `syncSource true`，保留无关配置。
6. 修改后读回目标段落，并汇报模块路径、远端仓库、覆盖文件和是否还需要 MGIT 同步。

## Safety

- 不修改 `xbuild/modules/default/*.gradle`，除非用户明确要求改基础映射。
- 不执行 `mgit sync`、`git checkout`、`git reset`、清理或删除操作，除非用户明确要求并确认。
- 如果 MGIT 预检失败，说明依赖问题，不要继续跑 MGIT。
- 如果同一个符号可能来自多个仓，先列候选和证据，让用户确认。
