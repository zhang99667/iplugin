---
name: mgit
version: 0.1.2
tags: [git, multi-repo, baidu, dev-tool]
description: 百度 MGIT 多仓库管理助手，仅当用户明确提到 MGIT/mgit、多仓库状态/同步/分支/批量提交推送，或需要同时操作多个子仓库时触发。不要因普通单仓 git status、git commit、分支解释或代码修改触发。
---

# MGIT 多仓库管理助手

MGIT 是基于 Git 的多仓库管理工具，用于在一个工作区内批量管理多个 Git 仓库。它适合百度 App iOS/Android 等由壳工程和多个业务/组件仓库组成的工程。

使用本技能时，先确认当前目录是否处于 MGIT 工作区，再根据用户目标选择最小影响范围的命令。MGIT 命令会同时影响多个仓库，默认优先只读检查；涉及写入、推送、删除或清理时，先说明影响范围和风险。

## Progressive Disclosure

SKILL.md 只保留触发、安全边界和命令路由。需要细节时按场景读取：

- `references/command-guide.md`：工作区识别、常用诊断、仓库范围控制、状态/同步/分支/拉取/提交/推送/forall 等命令。
- `references/config-troubleshooting.md`：manifest、本地配置、中间态处理、输出风格和常见意图映射。

## 触发边界

### 适用

用户明确提到 `MGIT`、`mgit`、多仓库管理、多仓库状态、同步、分支、批量提交/推送，或位于百度 App iOS/Android 壳工程中并需要同时处理多个子仓库。

### 不适用

用户只是处理普通单仓 Git 操作、查看单个仓库状态、写 commit message、解释 Git 概念或修改代码时，不使用本技能。

### 需要确认

涉及写入、推送、清理、删除、跨仓自定义命令或无法确定 MGIT 工作区范围时，先展示影响范围并等用户确认。

## 最短执行流程

1. 先判断是否真的是多仓 MGIT 任务；普通单仓 Git 不使用本技能。
2. 优先只读建立上下文：`mgit -w`、`mgit -l`、`mgit branch --compact`、`mgit status`。
3. 能限定仓库范围就限定，优先使用 `--mrepo`；不确定仓库名时先查 `mgit -l` 或 `mgit info <repo>`。
4. 写入、推送、清理、删除、`mgit forall -c` 自定义命令执行前，说明影响范围和风险，等待用户确认。
5. 需要具体命令时读取 `references/command-guide.md`；遇到 manifest、锁定仓库、中间态或冲突时读取 `references/config-troubleshooting.md`。

## 安全底线

- 不要盲目 `mgit init`、`mgit sync`、`mgit clean`、`mgit reset --hard`。
- 不要在日常 RD 流程里主动加 `--auto-exec` 或 `--no-check`。
- 不要把 `mgit clean` 当作解决问题的快捷方式；它会清空目标仓库工作区和暂存区。
- 不要对未知范围执行 `mgit forall -c` 写入命令。
- 用户没有明确要求推送时，不执行 `mgit push`。

## 输出风格

响应用户时保持简洁，优先给可执行命令和风险说明。当已经执行命令后，总结应包含：

- 执行了哪些 MGIT 命令。
- 哪些仓库受影响。
- 当前是否还有冲突、未提交改动或远端差异。
- 下一步建议。
