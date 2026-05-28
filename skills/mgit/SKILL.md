---
name: mgit
version: 0.1.1
tags: [git, multi-repo, baidu, dev-tool]
description: 百度 MGIT 多仓库管理助手，仅当用户明确提到 MGIT/mgit、多仓库状态/同步/分支/批量提交推送，或需要同时操作多个子仓库时触发。不要因普通单仓 git status、git commit、分支解释或代码修改触发。
---

# MGIT 多仓库管理助手

MGIT 是基于 Git 的多仓库管理工具，用于在一个工作区内批量管理多个 Git 仓库。它适合百度 App iOS/Android 等由壳工程和多个业务/组件仓库组成的工程。

使用本技能时，先确认当前目录是否处于 MGIT 工作区，再根据用户目标选择最小影响范围的命令。MGIT 命令会同时影响多个仓库，默认优先只读检查；涉及写入、推送、删除或清理时，先说明影响范围和风险。

## 触发边界

### 适用

用户明确提到 `MGIT`、`mgit`、多仓库管理、多仓库状态、同步、分支、批量提交/推送，或位于百度 App iOS/Android 壳工程中并需要同时处理多个子仓库。

### 不适用

用户只是处理普通单仓 Git 操作、查看单个仓库状态、写 commit message、解释 Git 概念或修改代码时，不使用本技能。

### 需要确认

涉及写入、推送、清理、删除、跨仓自定义命令或无法确定 MGIT 工作区范围时，先展示影响范围并等用户确认。

## 工作区识别

优先使用只读命令建立上下文：

```bash
mgit -w
mgit -l
mgit -al
mgit -v
```

- `mgit -w`：显示 MGIT 工程根目录，即 `.mgit` 所在目录。
- `mgit -l`：显示当前被 MGIT 管理的仓库。
- `mgit -al`：显示 manifest 内定义的全部仓库，包括未纳入管理或本地缺失的仓库。
- `mgit <command> --help`：确认本机 MGIT 版本支持的参数。

如果当前目录不在 MGIT 工作区，先让用户切到包含 `.mgit` 的工程目录，或搜索本地候选工程；不要盲目 `mgit init` 或 `mgit sync`。

## 常用诊断命令

```bash
mgit branch --compact
mgit status
mgit info <repo1> <repo2>
mgit log <repo> -n 20
mgit config -l
```

解释结果时按仓库归类，重点说明：

- 当前分支是否一致。
- 哪些仓库有工作区、暂存区、未跟踪或冲突文件。
- 哪些仓库相对远端超前、落后、分叉或游离 HEAD。
- 是否存在缺失仓库、锁定仓库或被排除仓库。

## 仓库范围控制

多数 MGIT 命令支持限定仓库范围。能限定就不要默认操作全部仓库。

```bash
mgit status --mrepo repoA repoB
mgit pull --mrepo repoA repoB
mgit push --mrepo repoA repoB
mgit status --el-mrepo repoA repoB
```

- `--mrepo`：只操作指定仓库，可指定多个，仓库名通常大小写不敏感。
- `--el-mrepo`：排除指定仓库，其余仓库执行。
- 不确定仓库名时先 `mgit -l` 或 `mgit info <repo>`。
- 不要混用 `--mrepo` 和 `--el-mrepo`，避免作用范围不清晰。

## 典型工作流

### 查看多仓库当前状态

```bash
mgit branch --compact
mgit status
```

输出给用户时给出短结论：是否干净、分支是否一致、哪些仓库需要处理。

### 下载缺失仓库或同步锁定仓库

```bash
mgit sync -n
mgit sync <repo>
mgit sync -c <repo1> <repo2>
mgit sync -ap
```

- `mgit sync`：同步被管理仓库，处理锁定仓库和缺失仓库。
- `mgit sync -n`：只下载配置中被管理但本地缺失的仓库，已有仓库不处理。
- `mgit sync -c repo`：下载指定仓库，包含未被 MGIT 管理的仓库。
- `mgit sync -p`：在同步基础上进一步 pull，影响更大，执行前先看状态。

### 切换或创建分支

```bash
mgit checkout <branch>
mgit checkout -b <branch>
mgit branch --compact
```

如果 manifest 中配置了 config-repo，MGIT 会优先切换配置仓库，再按新配置处理其他仓库。配置仓库有本地改动时，不要强行继续，先让用户确认提交、stash 或放弃。

### 拉取更新

```bash
mgit pull
mgit pull --mrepo repoA repoB
mgit pull --continue
mgit pull --abort
```

执行前先 `mgit status`。MGIT 会检查分支一致性和本地异常状态。遇到中间态时，先根据冲突/失败信息修复，再使用 `mgit pull --continue`；用户决定放弃时再使用 `mgit pull --abort`。

不要在日常 RD 流程里主动加 `--auto-exec` 或 `--no-check`。它们会跳过交互或检查，适合脚本化场景但风险较高。

### 批量提交

```bash
mgit add <path-or-options> --mrepo repoA
mgit commit -m "message" --mrepo repoA repoB
mgit aicommit
mgit aicommit <space-or-card>
```

- 先用 `mgit status` 或具体仓库 `git diff` 确认改动归属。
- 只 stage 用户要求的文件，不要把无关仓库一起提交。
- `mgit commit` 对没有暂存内容的仓库不会执行提交。
- MGIT 文档说明 `mgit commit` 不支持交互式操作，也不支持 `--amend`。
- `mgit aicommit` 可结合 iCafe 卡片生成提交内容；如需卡片信息，可再使用 iCafe 相关技能/工具。

### 推送审查分支

```bash
mgit push
mgit push --mrepo repoA repoB
mgit push --group-id <topic>
```

推送会影响远端审查系统，除非用户明确要求，否则不要执行。执行前说明将推送哪些仓库、当前分支、是否会创建远端分支或推到审查分支。

`mgit push` 默认偏自动化：无参数时通常让 MGIT 自动处理推送目标；`--group-id` 可把多仓库提交归到同一 topic。

### 批量执行自定义命令

```bash
mgit forall -c 'git status -s'
mgit forall -c 'git rev-parse --abbrev-ref HEAD' -n
mgit forall -c 'git clean -nd' --mrepo repoA
```

- `forall` 用于在多个仓库执行 shell 命令。
- `-n` 表示并发执行；读操作可用，写操作谨慎。
- 命令字符串要加引号。
- 自定义命令同样遵守最小范围原则，必要时加 `--mrepo`。

## 高风险命令

以下命令可能删除或覆盖本地改动，执行前必须先做只读检查并征得用户明确确认：

```bash
mgit clean
mgit reset --hard
mgit checkout -- <path>
mgit delete <repo>
mgit snap -r <snapshot_id>
mgit stash --clear
```

推荐流程：

1. 先运行 `mgit status` 展示受影响仓库。
2. 如果能缩小范围，改用 `--mrepo`。
3. 明确说明会丢弃/删除什么。
4. 用户确认后再执行。

不要把 `mgit clean` 当作解决问题的快捷方式。它等价于对目标仓库执行 `git add . && git reset --hard`，会清空工作区和暂存区。

## manifest 和本地配置

MGIT 配置通常位于：

- `.mgit/source-config/manifest.json`
- 配置仓库中的 `manifest.json`
- 可选的 `local_manifest.json`
- `.mgit/config.yml`

manifest 的关键字段：

- `remote`：远程仓库地址根目录。
- `dest`：仓库相对 MGIT 根目录的父路径。
- `repositories`：仓库列表。
- `remote-path`：远程仓库相对路径。
- `abs-dest`：仓库本地完整路径，优先于 `dest`。
- `config-repo`：配置仓库，最多一个。
- `mgit-excluded`：为 true 时不被 MGIT 操作。
- `lock`：锁定仓库到 branch、tag 或 commit_id。

本地调试优先使用 `local_manifest.json` 覆盖配置，不要随意改共享 manifest。常见命令：

```bash
mgit config -l
mgit config -c
mgit config -u <path_to>/local_manifest.json
mgit config -m manifest.json
```

## 中间态处理

`pull`、`merge`、`rebase` 可能进入 MGIT 中间态。不要重复启动新的同类操作。

处理步骤：

1. 读取 MGIT 输出和 `mgit status`，确认停在哪个仓库、原因是什么。
2. 进入具体仓库解决冲突或异常。
3. 使用对应命令继续：
   - `mgit pull --continue`
   - `mgit merge --continue`
   - `mgit rebase --continue`
4. 如果用户决定放弃，再使用对应 `--abort`。

## 输出风格

响应用户时保持简洁，优先给可执行命令和风险说明：

```markdown
建议先跑：
`mgit branch --compact && mgit status`

如果只处理广告相关仓库，再用：
`mgit pull --mrepo ad_business lib_ad lib_ad_runtime`

注意：不要直接 `mgit pull --no-check`，它会跳过状态检查，容易把本地异常带进合并。
```

当已经执行命令后，总结应包含：

- 执行了哪些 MGIT 命令。
- 哪些仓库受影响。
- 当前是否还有冲突、未提交改动或远端差异。
- 下一步建议。

## 常见意图映射

- “看一下多仓库状态” → `mgit branch --compact` + `mgit status`
- “哪些仓库没拉下来” → `mgit -l` 或 `mgit -al`，必要时确认后 `mgit sync -n`
- “只拉某几个仓库” → `mgit pull --mrepo ...`
- “把缺失仓库补齐” → `mgit sync -n`
- “切到某分支” → 先 `mgit status`，再 `mgit checkout <branch>`
- “批量跑一个 git 命令” → `mgit forall -c '...'`，只读可考虑 `-n`
- “推多仓库评审” → 先 `mgit status`，确认超前仓库，再 `mgit push --mrepo ...` 或 `mgit push --group-id ...`
- “MGIT 卡住/冲突/中间态” → 诊断具体仓库，修复后 `--continue` 或确认后 `--abort`
