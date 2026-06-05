# MGIT 命令指南

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
- 在百度 EasyBox/xbuild 工程中，如果用户提到 `modules*.gradle`、`overlay/local`、`syncSource`、源码模式、开发分支上车或 master 合入，先读取 `references/easybox-overlay-local.md`，用实际改动仓库推断候选模块路径和基础配置文件，并通过 `mgit -l` / `mgit info` 验证后再用于 `--mrepo` 或 EasyBox 配置编辑。

## 查看多仓库状态

```bash
mgit branch --compact
mgit status
```

输出给用户时给出短结论：是否干净、分支是否一致、哪些仓库需要处理。

## 下载缺失仓库或同步锁定仓库

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

## 切换或创建分支

```bash
mgit checkout <branch>
mgit checkout -b <branch>
mgit branch --compact
```

如果 manifest 中配置了 config-repo，MGIT 会优先切换配置仓库，再按新配置处理其他仓库。配置仓库有本地改动时，不要强行继续，先让用户确认提交、stash 或放弃。

## 拉取更新

```bash
mgit pull
mgit pull --mrepo repoA repoB
mgit pull --continue
mgit pull --abort
```

执行前先 `mgit status`。MGIT 会检查分支一致性和本地异常状态。遇到中间态时，先根据冲突/失败信息修复，再使用 `mgit pull --continue`；用户决定放弃时再使用 `mgit pull --abort`。

不要在日常 RD 流程里主动加 `--auto-exec` 或 `--no-check`。它们会跳过交互或检查，适合脚本化场景但风险较高。

## 批量提交

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

## 推送审查分支

```bash
mgit push
mgit push --mrepo repoA repoB
mgit push --group-id <topic>
```

推送会影响远端审查系统，除非用户明确要求，否则不要执行。执行前说明将推送哪些仓库、当前分支、是否会创建远端分支或推到审查分支。

`mgit push` 默认偏自动化：无参数时通常让 MGIT 自动处理推送目标；`--group-id` 可把多仓库提交归到同一 topic。

## 批量执行自定义命令

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
