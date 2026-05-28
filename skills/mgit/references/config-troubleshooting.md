# MGIT 配置与中间态处理

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

- “看一下多仓库状态” -> `mgit branch --compact` + `mgit status`
- “哪些仓库没拉下来” -> `mgit -l` 或 `mgit -al`，必要时确认后 `mgit sync -n`
- “只拉某几个仓库” -> `mgit pull --mrepo ...`
- “把缺失仓库补齐” -> `mgit sync -n`
- “切到某分支” -> 先 `mgit status`，再 `mgit checkout <branch>`
- “批量跑一个 git 命令” -> `mgit forall -c '...'`，只读可考虑 `-n`
- “推多仓库评审” -> 先 `mgit status`，确认超前仓库，再 `mgit push --mrepo ...` 或 `mgit push --group-id ...`
- “MGIT 卡住/冲突/中间态” -> 诊断具体仓库，修复后 `--continue` 或确认后 `--abort`
