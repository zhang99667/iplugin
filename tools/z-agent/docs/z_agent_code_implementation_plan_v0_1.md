# z-agent 代码实施方案 v0.1.0

> 来源文档：`docs/z_agent_session_restore_plan_v0_1.html`
>
> 版本记录：`../versions/v0.1.0.md`
>
> 状态：实施方案草案。本文不要求完全照搬 HTML，而是把可直接编码的落地路径、建议调整点、模块边界和验证清单拆出来，供后续 review 后实施。

## 1. 目标与边界

### 1.1 本期目标

实现一个独立的 `tools/z-agent` Python CLI 子项目，用于：

1. 记录 Ghostty 当前 window / tab / split / terminal pane 工作区快照。
2. 将每个 pane 与当时运行的 Codex 或 Claude Code session 绑定。
3. 在恢复时重建 Ghostty 布局，并在对应 pane 中执行 agent 原生 resume 命令。
4. `zagent restore` 只负责执行恢复，不再暴露额外执行模式。

### 1.2 明确不做

1. 不恢复进程内存、PTY、未完成 tool call。
2. 不读取对话转录正文，只读取 session 元数据和路径。
3. 不回放任意历史 shell 命令。
4. 不自动修改用户 `.zshrc` / shell profile。
5. 不做 daemon / launchd，状态更新由 wrapper、hook 和用户显式命令触发。

### 1.3 当前仓库现实

当前 `tools/z-agent` 只有文档和空目录：

```text
tools/z-agent/
  docs/z_agent_session_restore_plan_v0_1.html
  src/
  tests/
  versions/
```

因此 v0.1.0 的第一步不是“改现有代码”，而是补齐 tool 子项目脚手架：

```text
tools/z-agent/
  README.md
  CHANGELOG.md
  pyproject.toml
  versions/v0.1.0.md
  src/z_agent/
  tests/
```

## 2. 对 HTML 方案的建议调整

这些调整不是最终决定，编码前建议和 owner 确认。

### 2.1 `restore_cmd` 从字符串升级为结构化命令

HTML 中状态示例把 `restore_cmd` 存成字符串：

```json
"restore_cmd": "codex resume 019e9d90-07e9-79c3-93c3-a5b6952aaf4f"
```

建议状态里同时保存结构化字段：

```json
{
  "restore": {
    "kind": "agent_resume",
    "agent": "codex",
    "argv": ["codex", "resume", "019e9d90-07e9-79c3-93c3-a5b6952aaf4f"],
    "display": "codex resume 019e9d90-07e9-79c3-93c3-a5b6952aaf4f"
  }
}
```

原因：

1. planner 可以基于 `argv` 做白名单校验，避免 shell 字符串注入。
2. 内部计划仍保留 `display`，便于日志和错误信息展示。
3. restore adapter 生成 AppleScript 输入时统一从 `argv` 安全转义。

兼容方式：v0.1.0 可以继续写 `restore_cmd` 作为兼容展示字段，但执行只信任 `restore.argv`。

### 2.2 Ghostty AppleScript 先做能力探测

HTML 假设 AppleScript 能稳定读取 windows / tabs / terminals / cwd / split 信息。实际落地时建议先实现 `ghostty probe` 或 `doctor` 内部探测：

1. Ghostty 是否安装、是否运行。
2. `osascript` 是否能访问 Ghostty，Automation 权限是否可用。
3. 当前 Ghostty AppleScript dictionary 是否暴露 `windows`、`tabs`、`terminals`、`working directory`。
4. split tree 是否能直接读取；如果不能，只保存 pane 顺序和 split 方向的低保真结构。

原因：Ghostty AppleScript API 版本差异或权限问题会直接影响 capture/restore，早失败比恢复时半执行更安全。

### 2.3 terminal marker 作为高置信绑定，不作为唯一绑定

HTML 的主要绑定方式是 wrapper 写入 terminal title/name marker：

```text
__zagent_terminal_<id>__
```

建议保留该方式，但实现时增加降级路径：

1. 优先从 Ghostty terminal title/name 提取 marker，命中为 `binding_confidence=high`。
2. marker 不可读时，用 `cwd + agent process + last_seen_at 时间窗` 做低置信匹配，标记为 `binding_confidence=low`。
3. low 置信度的 pane 不自动输入 resume，避免把 session 贴到错误窗格。

原因：不同 shell、prompt、terminal title 策略可能覆盖 wrapper 写入的 title，不能把 marker 读取视为绝对可靠。

### 2.4 `terminal_key` 生命周期改为“pane 绑定优先，run_id 区分进程”

HTML 里 wrapper 每次启动生成 `terminal_key` 和 `run_id`。建议细化：

1. 如果当前环境已有 `Z_AGENT_TERMINAL_KEY`，wrapper 默认复用，表示同一个 pane 的连续 agent 生命周期。
2. 如果没有，则生成新的 `terminal_key`。
3. 每次 wrapper 启动真实 agent 都生成新的 `run_id`。

原因：同一个 Ghostty pane 中重启 Codex/Claude 后，session 变化但 pane 身份不应该频繁漂移；`run_id` 才是一次进程启动的诊断标识。

需要讨论：如果用户在同一个 pane 中先启动 Codex 再启动 Claude，是否复用同一个 `terminal_key`。建议复用 pane key，但 `active_terminals[terminal_key].agent` 更新为最后一次 agent。

### 2.5 restore 收敛为单一执行入口

HTML 草案曾把“查看计划”“真正恢复”“只输入不回车”“只打印脚本”拆成多个命令参数。当前实现收敛为最简单的语义：

```bash
zagent restore
```

含义：

1. `zagent restore` 控制 Ghostty 执行恢复。
2. 执行前仍由 planner 做结构化白名单校验。
3. 不再提供恢复命令的额外调试参数。

### 2.6 state 文件写入必须有锁和坏文件备份

HTML 已提出“临时文件 + rename”和 lock 文件。建议 v0.1.0 必须实现，不能留到后续：

1. 写入前获取 `workspace_state.json.lock`。
2. 读到损坏 JSON 时备份为 `workspace_state.json.broken.<timestamp>`。
3. 写入使用同目录临时文件，`fsync` 后 `replace`。

原因：hook ingest 可能高频触发，snapshot capture 也会写同一个状态文件；没有锁会偶现状态丢失。

## 3. 目标文件结构

```text
tools/z-agent/
  README.md
  CHANGELOG.md
  pyproject.toml
  versions/
    v0.1.0.md
  docs/
    z_agent_session_restore_plan_v0_1.html
    z_agent_code_implementation_plan_v0_1.md
  src/
    z_agent/
      __init__.py
      __main__.py
      agent_specs.py
      cli.py
      config.py
      doctor.py
      ghostty.py
      hooks.py
      install.py
      models.py
      planner.py
      state.py
      wrapper.py
      applescript/
        capture.scpt
        restore.scpt
      templates/
        hook_ingest.sh
  tests/
    fixtures/
      hook_codex.json
      hook_claude.json
      ghostty_capture.json
      workspace_state.json
    test_agent_specs.py
    test_hooks.py
    test_planner.py
    test_state.py
    test_wrapper.py
```

## 4. 模块职责

### 4.1 `agent_specs.py`

定义每个 agent 的差异：

```python
AgentSpec(
    name="codex",
    binary_names=("codex",),
    env_binary_var="Z_AGENT_CODEX_BINARY",
    resume_argv_template=("codex", "resume", "{session_id}"),
    session_roots=("~/.codex/sessions",),
)
```

Claude Code：

```python
AgentSpec(
    name="claude",
    binary_names=("claude",),
    env_binary_var="Z_AGENT_CLAUDE_BINARY",
    resume_argv_template=("claude", "--resume", "{session_id}"),
    session_roots=("~/.claude/projects", "~/.claude"),
)
```

职责：

1. 查找真实 binary。
2. 生成 resume argv。
3. 校验 agent 名称。
4. 为 install/hook/planner 提供统一配置。

### 4.2 `models.py`

集中定义 dataclass 或 TypedDict：

1. `ActiveTerminal`
2. `WorkspaceState`
3. `WorkspaceSnapshot`
4. `WindowSnapshot`
5. `TabSnapshot`
6. `PaneSnapshot`
7. `RestoreCommand`
8. `RestorePlan`

原则：

1. 对外 JSON schema 保持稳定。
2. 内部模型负责默认值和兼容字段转换。
3. 所有时间使用 ISO 8601，保留本地时区 offset。

### 4.3 `state.py`

状态文件路径：

```text
${Z_AGENT_STATE_DIR:-~/.local/share/z-agent}/workspace_state.json
```

必须提供：

1. `load_state()`
2. `save_state(state)`
3. `update_active_terminal(terminal_key, patch)`
4. `save_latest_workspace(snapshot)`
5. `backup_broken_state(path)`

写入要求：

1. lock 文件防并发。
2. 临时文件 + 原子 replace。
3. JSON 损坏时备份并初始化空状态。
4. `latest_workspace` 更新前移动旧值到 `previous_workspace`。

### 4.4 `wrapper.py`

命令：

```bash
python3 src/z_agent/cli.py codex [args...]
python3 src/z_agent/cli.py claude [args...]
```

流程：

1. 解析 agent。
2. 找真实 binary。
3. 生成或复用 `terminal_key`。
4. 生成 `run_id`。
5. 写 terminal marker。
6. 预写 `active_terminals[terminal_key]`。
7. 设置 `Z_AGENT_TERMINAL_KEY`、`Z_AGENT_RUN_ID`、`Z_AGENT_CWD`、`Z_AGENT_STATE_DIR`、`Z_AGENT_AGENT`。
8. `exec` 真实 agent binary，透传参数和退出码。

失败策略：

1. 找不到真实 binary：退出非 0，并提示 `--binary`、agent env var 或 `PATH` 修复方式。
2. 状态写入失败：stderr warning，但不阻止启动真实 agent。
3. marker 写入失败：stderr warning，并继续启动。

### 4.5 `hooks.py`

命令：

```bash
zagent hook ingest --agent codex --json < hook-event.json
zagent hook ingest --agent claude --json < hook-event.json
```

职责：

1. 从 stdin 读取 hook JSON。
2. 从环境读取 `Z_AGENT_TERMINAL_KEY`、`Z_AGENT_CWD`、`Z_AGENT_RUN_ID`。
3. 根据 agent spec 提取 `session_id`、`session_file`。
4. 生成 `restore.argv` 和兼容 `restore_cmd`。
5. 更新 `active_terminals`。

提取策略：

1. 先读取 payload 中明确的 session 字段。
2. 再从 transcript/session 文件路径推断 session id。
3. 仍失败则写入 `resumable=false`，保留 cwd、agent、last_seen_at。

### 4.6 `ghostty.py`

职责：

1. 执行 `osascript`。
2. capture 当前 Ghostty 布局。
3. restore 时生成 AppleScript。
4. 将 AppleScript 输出转换为内部 `WorkspaceSnapshot`。
5. 将 `OSError`、权限失败、Ghostty 未运行等错误转换成用户可读诊断。

建议拆两层：

1. `GhosttyAdapter`：真实执行 `osascript`。
2. `GhosttyScriptBuilder`：纯函数生成 capture/restore 脚本，便于单测。

### 4.7 `planner.py`

职责：

1. 从 `latest_workspace` 生成恢复计划文本。
2. 校验每个 pane 的 restore 命令。
3. 区分 agent pane 和普通 shell pane。
4. 拒绝执行低置信绑定或非法命令。

执行白名单：

1. `["codex", "resume", <session_id>]`
2. `["claude", "--resume", <session_id>]`

session id 校验：

1. 不允许空字符串。
2. 不允许包含 shell metacharacters。
3. 建议接受 UUID、ULID、路径派生 ID；具体格式由 agent extractor 决定，但执行前必须是单个 argv token。

### 4.8 `install.py`

命令：

```bash
zagent install codex
zagent install claude
```

安装目录：

```text
~/.z-agent/<agent>/
  config/hooks/<agent>-native-hooks.json
  config/hooks/<agent>-hook-ingest.sh
```

职责：

1. 写入 hook ingest shell 和 native hook 模板。
2. 不自动修改 `.zshrc`。
3. 不生成同名 PATH wrapper，不接管用户原始 `codex` / `claude` 命令。

## 5. CLI 命令契约

```bash
# 诊断，不写文件
python3 src/z_agent/cli.py doctor
zagent doctor

# wrapper，启动真实 agent
python3 src/z_agent/cli.py codex [codex args...]
python3 src/z_agent/cli.py claude [claude args...]

# 安装
zagent install codex
zagent install claude

# hook ingest
zagent hook ingest --agent codex --json < hook-event.json
zagent hook ingest --agent claude --json < hook-event.json

# 状态查看
zagent state show
zagent state show --json

# 快照采集
zagent snapshot capture --name working-now

# 恢复
zagent restore
```

## 6. 状态 JSON 草案

```json
{
  "schema": 1,
  "updated_at": "2026-06-13T14:30:15+08:00",
  "active_terminals": {
    "za_terminal_a1b2c3d4": {
      "terminal_key": "za_terminal_a1b2c3d4",
      "marker": "__zagent_terminal_a1b2c3d4__",
      "agent": "codex",
      "cwd": "/Users/markz/code/tools/iplugin",
      "run_id": "za_run_6f7e8d9c",
      "session_id": "019e9d90-07e9-79c3-93c3-a5b6952aaf4f",
      "session_file": "~/.codex/sessions/2026/06/13/rollout-example.jsonl",
      "restore": {
        "kind": "agent_resume",
        "agent": "codex",
        "argv": [
          "codex",
          "resume",
          "019e9d90-07e9-79c3-93c3-a5b6952aaf4f"
        ],
        "display": "codex resume 019e9d90-07e9-79c3-93c3-a5b6952aaf4f"
      },
      "restore_cmd": "codex resume 019e9d90-07e9-79c3-93c3-a5b6952aaf4f",
      "resumable": true,
      "last_seen_at": "2026-06-13T14:29:42+08:00",
      "source": "agent_hook"
    }
  },
  "latest_workspace": {
    "snapshot_id": "ws_20260613_143015",
    "name": "working-now",
    "captured_at": "2026-06-13T14:30:15+08:00",
    "terminal_app": "Ghostty",
    "windows": []
  },
  "previous_workspace": null
}
```

## 7. 迭代拆分

### Phase 0：项目脚手架

交付：

1. `pyproject.toml`
2. `README.md`
3. `CHANGELOG.md`
4. `versions/v0.1.0.md`
5. `src/z_agent/__init__.py`
6. `src/z_agent/__main__.py`
7. `src/z_agent/cli.py`
8. 空跑命令：`doctor`、`state show`

验证：

```bash
python3 src/z_agent/cli.py doctor
python3 -m z_agent --help
python3 -m pytest
```

### Phase 1：状态存储

交付：

1. `state.py`
2. `models.py`
3. state 文件初始化、读取、更新、原子写。
4. 损坏 JSON 备份。

验证：

1. 新状态文件可初始化。
2. 更新 `active_terminals` 不覆盖其他字段。
3. 保存 latest workspace 时旧值进入 `previous_workspace`。
4. 并发写入不会生成半截 JSON。

### Phase 2：agent specs 与 hook ingest

交付：

1. `agent_specs.py`
2. `hooks.py`
3. Codex / Claude session id 提取器。
4. `restore.argv` 生成。

验证：

1. fixture hook payload 能提取 session id。
2. 缺少 terminal key 时返回非 0。
3. 缺少 session id 时写入 `resumable=false`。
4. restore argv 只生成白名单命令。

### Phase 3：wrapper

交付：

1. `wrapper.py`
2. `zagent codex`
3. `zagent claude`
4. terminal marker 写入。
5. 真实 binary 查找和 exec。

验证：

1. 使用假的 agent binary 捕获 env，确认 `Z_AGENT_*` 注入。
2. 真实 binary 不存在时错误可读。
3. 状态写入失败不阻塞 fake agent 启动。
4. 已存在 `Z_AGENT_TERMINAL_KEY` 时复用 key，新建 run id。

### Phase 4：install

交付：

1. `install.py`
2. hook ingest shell 模板。
3. native hook 配置模板。

验证：

1. 写入预期 hook 目录。
2. 不修改 `.zshrc`。
3. 不生成 `bin/<agent>` 或 `<agent>.zsh`。

### Phase 5：Ghostty capture

交付：

1. `ghostty.py`
2. `applescript/capture.scpt`
3. `zagent snapshot capture`
4. marker 绑定逻辑。

验证：

1. fixture capture JSON 能生成 workspace snapshot。
2. marker 命中为 high。
3. marker 缺失时 low confidence。
4. Ghostty 未运行或无权限时错误可读。

### Phase 6：restore planner

交付：

1. `planner.py`
2. `zagent restore`
3. 白名单校验。

验证：

1. 无 `latest_workspace` 时提示先 capture。
2. 非白名单 argv 拒绝执行。
3. low confidence pane 默认不自动执行。

### Phase 7：Ghostty 恢复执行

交付：

1. `applescript/restore.scpt`
2. `zagent restore`

验证：

1. 在对应 pane 输入 resume 并回车。
2. AppleScript 中命令输入经过转义。

## 8. 测试策略

### 8.1 单元测试优先覆盖纯逻辑

必须覆盖：

1. agent spec 查找和 resume argv。
2. hook payload 提取。
3. state load/save/update。
4. planner 白名单校验。
5. AppleScript 字符串转义。
6. wrapper env 构造。

### 8.2 Ghostty 集成测试手动执行

自动化测试不默认控制真实 Ghostty。提供手动验证脚本或 README 步骤：

1. 打开 Ghostty。
2. 创建多个 tab/split。
3. 用 z-agent wrapper 启动 fake 或真实 agent。
4. capture。
5. 执行 `zagent restore`。

### 8.3 不依赖真实 Codex/Claude 的 fixture

CI/本地单测使用 fake binary：

```bash
#!/usr/bin/env bash
env | sort > "$Z_AGENT_TEST_ENV_OUT"
```

这样 wrapper 和 install 可以稳定测试，不依赖用户机器的真实 agent CLI。

## 9. 风险与对策

| 风险 | 对策 | v0.1.0 要求 |
| --- | --- | --- |
| Ghostty AppleScript 字段不可用 | doctor/probe 先探测，capture 失败时给出指引 | 必做 |
| terminal marker 被覆盖 | marker high confidence，cwd/process low confidence | 必做 |
| low confidence 错绑 session | 默认恢复时拒绝自动执行 | 必做 |
| restore 执行任意命令 | 只执行结构化白名单 argv | 必做 |
| state 并发写坏 | lock + atomic replace | 必做 |
| hook payload 字段变化 | extractor 分层解析，失败写 `resumable=false` | 必做 |
| install 误改用户环境 | 只生成 hook 文件，不改 `.zshrc`，不接管原始 Agent 命令 | 必做 |

## 10. Review 决策点

编码前建议确认以下问题：

1. `restore_cmd` 是否接受升级为 `restore.argv + restore.display`，并保留 `restore_cmd` 兼容字段。
2. `terminal_key` 是否按“同 pane 复用，run_id 区分进程”的策略实现。
3. low confidence pane 是否默认禁止自动 resume。
4. v0.1.0 是否只支持 Ghostty，其他 terminal 明确排除。
5. Codex / Claude hook payload 的真实样例是否需要先采集一轮再实现 extractor。

## 11. 建议实施顺序

推荐按下面顺序提交，每一步都可独立验证：

1. 提交脚手架、README、CHANGELOG、版本记录、CLI 空命令。
2. 提交 state store 和模型。
3. 提交 agent specs、hook ingest、planner 白名单。
4. 提交 wrapper 和 fake binary 测试。
5. 提交 install 和模板生成。
6. 提交 Ghostty capture adapter，先支持脚本预览和可测试输出。
7. 提交 restore planner。
8. 最后提交恢复执行能力。

这样可以把高风险的 Ghostty GUI 自动化放到后面，同时先把状态模型、命令安全和 hook 链路稳定下来。
