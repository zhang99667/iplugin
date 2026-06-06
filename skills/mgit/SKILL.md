---
name: mgit
version: 0.1.5
tags: [git, multi-repo, baidu, dev-tool]
description: 百度 MGIT 多仓库管理助手。当任务上下文显示当前工作区可能是 MGIT/多仓库工程，或用户需要查看、同步、比较、提交、推送多个子仓库时触发，即使用户没有明确说 mgit；涉及百度 EasyBox/xbuild modules 配置、overlay/local、modules-local*.gradle、syncSource、本地源码模式或多仓模块范围判断时也触发；遇到 Ruby/gem/colored2 等 MGIT 启动依赖问题时先诊断环境。优先用于只读诊断多仓状态、分支、仓库范围和中间态；普通单仓 git 操作不触发。涉及写入、同步、推送、清理、reset 或跨仓自定义命令时必须先确认影响范围。
---

# MGIT 多仓库管理助手

MGIT 是基于 Git 的多仓库管理工具，用于在一个工作区内批量管理多个 Git 仓库。它适合百度 App iOS/Android 等由壳工程和多个业务/组件仓库组成的工程。

使用本技能时，不要求用户必须点名 `mgit`。当任务明显涉及多仓库工程、壳工程和多个业务/组件仓库，或当前目录可能处于 MGIT 工作区时，模型应主动判断是否需要 MGIT 来建立上下文。MGIT 命令会同时影响多个仓库，默认优先只读检查；涉及写入、推送、删除或清理时，先说明影响范围和风险。

## Progressive Disclosure

SKILL.md 只保留触发、安全边界和命令路由。需要细节时按场景读取：

- `references/command-guide.md`：工作区识别、常用诊断、仓库范围控制、状态/同步/分支/拉取/提交/推送/forall 等命令。
- `references/config-troubleshooting.md`：manifest、本地配置、中间态处理、输出风格和常见意图映射。
- `references/easybox-overlay-local.md`：百度 EasyBox/xbuild `modules*.gradle`、`syncSource`、开发分支 `overlay` 与 master 合入 `local` 的上车配置流程。

## 触发边界

### 适用

- 用户明确提到 `MGIT`、`mgit`、多仓库管理、多仓库状态、同步、分支、批量提交/推送。
- 用户没有点名 MGIT，但任务需要同时判断多个子仓库状态、分支、远端差异、中间态、冲突、依赖仓库位置或壳工程内的仓库范围。
- 当前目录位于百度 App iOS/Android 壳工程，用户的问题明显跨业务/组件仓库，例如“整体看一下状态”“这些改动在哪些仓”“同步一下这套工程”“为什么这个模块分支不对”。
- 当前目录位于百度 EasyBox/xbuild 工程，用户提到 `modules-local*.gradle`、`modules-overlay*.gradle`、`syncSource`、源码模式、本地模块配置、开发分支上车、master 合入或某组模块对应哪些仓库。

### 不适用

用户只是处理普通单仓 Git 操作、查看单个仓库状态、写 commit message、解释 Git 概念、修改当前仓库代码，或当前任务可以用本仓库内的 `git` 命令明确完成时，不使用本技能。

### 需要确认

涉及写入、同步、推送、清理、删除、reset、跨仓自定义命令或无法确定 MGIT 工作区范围时，先展示影响范围并等用户确认。只读诊断命令可以在判断需要时主动执行。

## 最短执行流程

1. 先判断是否真的是多仓 MGIT 任务；用户没有点名 mgit 也可以触发，但普通单仓 Git 不使用本技能。
2. 第一次准备执行 MGIT，或刚切换 shell/Ruby/rbenv 环境时，先做轻量启动依赖预检：

```bash
which mgit
ruby -v
ruby -e 'require "colored2"; require "peach"; require "tty-pager"; require "logger"; puts "mgit ruby deps ok"'
```

3. 如果预检出现 `cannot load such file -- colored2`、`peach`、`tty-pager` 或 `logger`，不要继续跑 `mgit`。先说明 MGIT 还没执行到多仓逻辑，是当前 Ruby gem path 缺依赖；除非用户明确要求安装，否则只给修复命令：

```bash
gem install colored2 -v 3.1.2
gem install peach -v '~> 0.5'
gem install tty-pager -v '~> 0.12'
gem install logger -v '~> 1.4.2'
rbenv rehash
```

4. 如果预检依赖通过，但出现 `rbenv ... cannot create temp file`，这是当前执行环境不允许 rbenv 写临时文件，不是 MGIT 工作区问题。可在普通终端重试，或在当前工具环境申请可写/非沙箱执行权限后再跑 MGIT。
5. 预检通过后，优先只读建立上下文：`mgit -w`、`mgit -l`、`mgit branch --compact`、`mgit status`。
6. 在 EasyBox/xbuild 场景中，如果用户提到 `syncSource`、`overlay/local` 或上车配置，读取 `references/easybox-overlay-local.md`，先用实际改动仓库推断需要开启源码模式的模块范围。
7. 能限定仓库范围就限定，优先使用 `--mrepo`；不确定仓库名时先查 `mgit -l` 或 `mgit info <repo>`。
8. 写入、推送、清理、删除、`mgit forall -c` 自定义命令执行前，说明影响范围和风险，等待用户确认。
9. 需要具体命令时读取 `references/command-guide.md`；遇到 manifest、锁定仓库、中间态或冲突时读取 `references/config-troubleshooting.md`。

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
