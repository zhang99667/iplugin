# z-agent

`z-agent` 是一个本地命令行工具，用来记录 Ghostty 里的 Codex / Claude Code 会话信息，并在需要时恢复工作区。

它不会读取对话转录正文，不回放命令行历史，也不会自动改你的 shell 配置文件。你需要显式用 `zagent codex` 或 `zagent claude` 启动智能体，它才会记录当前终端窗格的身份和会话元数据。

## 一句话流程

```bash
cd tools/z-agent
python3 -m pip install -e .
zagent doctor
zagent install codex
zagent codex
zagent snapshot capture --name working-now
zagent restore
```

上面这组命令只展示最短链路。第一次使用时，还需要把 `zagent install` 生成的钩子示例合并到 Codex / Claude Code 自己的钩子配置里，具体见下面步骤。

## 安装

进入工具目录后安装本地可编辑版本：

```bash
cd tools/z-agent
python3 -m pip install -e .
```

检查本机环境：

```bash
zagent doctor
```

`doctor` 会检查状态文件位置、安装目录、Codex / Claude Code 命令是否能找到，以及常见会话目录是否存在。

## 生成钩子文件

Codex：

```bash
zagent install codex
```

Claude Code：

```bash
zagent install claude
```

安装命令会生成两类文件：

```text
~/.z-agent/<agent>/config/hooks/<agent>-hook-ingest.sh
~/.z-agent/<agent>/config/hooks/<agent>-native-hooks.json
```

其中：

- `*-hook-ingest.sh` 是真正被智能体钩子调用的脚本。
- `*-native-hooks.json` 是配置示例，需要你手动合并到对应智能体的原生钩子配置里。

`z-agent` 不会直接覆盖 Codex / Claude Code 的原配置，避免破坏你已有的钩子。

## 启动智能体

需要记录会话时，不要直接运行 `codex` 或 `claude`，改用：

```bash
zagent codex
zagent claude
```

真实智能体参数可以原样放在后面：

```bash
zagent codex --model gpt-5
zagent claude --resume <session_id>
```

如果 `zagent` 找不到真实命令，或者你的机器上有多个版本，可以显式指定：

```bash
zagent codex --binary /path/to/codex --model gpt-5
zagent claude --binary /path/to/claude
```

也可以用环境变量长期指定：

```bash
export Z_AGENT_CODEX_BINARY=/path/to/codex
export Z_AGENT_CLAUDE_BINARY=/path/to/claude
```

启动时，`z-agent` 会做三件事：

- 给当前终端窗格生成或复用一个 `terminal_key`。
- 把 `Z_AGENT_TERMINAL_KEY`、`Z_AGENT_RUN_ID`、`Z_AGENT_CWD` 注入到真实智能体子进程环境里。
- 把由 `terminal_key` 派生的标题标记写入终端标题，方便后续 Ghostty 快照识别这个窗格。

## 查看状态

查看摘要：

```bash
zagent state show
```

查看完整 JSON：

```bash
zagent state show --json
```

默认状态文件位置：

```text
~/.local/share/z-agent/workspace_state.json
```

如需换目录：

```bash
export Z_AGENT_STATE_DIR=/path/to/state-dir
```

## 采集快照

在 Ghostty 当前工作区里运行：

```bash
zagent snapshot capture --name working-now
```

这会通过 Ghostty AppleScript 读取当前窗口、标签页、pane、标题和工作目录，并写入状态文件。

## 恢复工作区

```bash
zagent restore
```

`restore` 会读取最近一次快照，重建 Ghostty 工作区，并在可恢复的智能体窗格里执行原生 resume 命令。

## 安全边界

- 自动恢复只允许 `codex resume <session_id>` 和 `claude --resume <session_id>`。
- `restore_cmd` 只是兼容字段，真实执行只信任结构化 `restore.argv`。
- 低置信度窗格绑定不自动执行。
- 状态写入使用锁文件和原子替换。
- 不读取对话转录正文。
- 不回放任意命令行历史。

## 常见问题

### `zagent: 找不到真实 codex binary`

说明 `z-agent` 在 `PATH` 里找不到真实 `codex`。可以用：

```bash
zagent codex --binary /path/to/codex
```

或者设置：

```bash
export Z_AGENT_CODEX_BINARY=/path/to/codex
```

Claude Code 同理使用 `Z_AGENT_CLAUDE_BINARY`。

### `restore` 没有可恢复命令

通常有三种原因：

- 这个智能体不是通过 `zagent codex` / `zagent claude` 启动的。
- 原生钩子配置还没有合并，会话 id 没有写入状态文件。
- 当前窗格只是通过工作目录低置信度匹配到，不能自动执行恢复命令。

可以先看状态：

```bash
zagent state show --json
```

### `restore` 没有控制 Ghostty

第一次控制 Ghostty 时，macOS 可能需要你授权当前终端或 Python 控制 Ghostty。授权后再运行一次。

## 开发验证

运行子项目测试：

```bash
python3 -B -m unittest discover -s tests
```

在仓库根目录运行插件结构校验：

```bash
python3 scripts/validate-plugin.py
```

设计记录见 `docs/` 和 `versions/`。
