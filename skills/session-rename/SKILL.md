---
name: session-rename
version: 0.1.1
tags: [claude-code, session, hooks, productivity]
description: Claude Code 会话命名助手，仅当用户明确要求重命名当前会话、给当前对话起标题、自动命名 Claude Code 会话，或配置 UserPromptSubmit sessionTitle hook 时触发。不要因命名分支、PR、文件、项目或 Codex 对话触发。
---

# Claude Code 会话命名助手

目标：让 Claude Code 会话自动获得短而可检索的标题，方便用户后续从会话列表里找回上下文。

优先方案是配置 `UserPromptSubmit` hook，在用户每次提交 prompt 时由本地脚本返回 `sessionTitle`。这是官方支持的会话标题设置方式，比直接修改 `~/.claude/sessions/*.json` 更安全。

## 触发边界

### 适用

使用本技能处理这些请求：

- 用户要求“自动重命名会话”“以后都帮我给会话命名”。
- 用户说找不到会话，因为会话没有 rename/title。
- 用户要求“根据第一轮对话给当前会话起名”。
- 用户询问能否用 hook 或其他方式自动更新会话标题。

### 不适用

不要用于给代码分支、PR、commit、文件、业务项目或普通文档改名。非 Claude Code 环境里不要建议编辑 `.claude` 配置。

### 需要确认

如果当前平台不是 Claude Code，先说明该技能只适用于 Claude Code；如果用户只是要一个标题建议，可以只给标题，不修改本地配置。

## 推荐实现：UserPromptSubmit hook

Claude Code 的 `UserPromptSubmit` hook 会在用户提交 prompt 后、Claude 正式处理前运行。hook 输入 JSON 通常包含：

```json
{
  "session_id": "...",
  "transcript_path": "/Users/.../.claude/projects/.../<session>.jsonl",
  "cwd": "/Users/...",
  "hook_event_name": "UserPromptSubmit",
  "prompt": "用户刚提交的内容"
}
```

该 hook 可以向 stdout 输出 JSON：

```json
{"sessionTitle":"add-mgit-skill"}
```

Claude Code 会用 `sessionTitle` 设置会话标题。

## 自动命名策略

hook 脚本应快速、稳定、无副作用：

1. 读取 stdin JSON。
2. 从 `prompt` 中提取主题。
3. 必要时读取 `transcript_path` 判断是否是会话前几轮。
4. 生成英文 kebab-case 标题。
5. 输出且只输出合法 JSON 到 stdout。

标题规则：

- 英文 kebab-case。
- 3 到 6 个词，约 20 到 50 个字符。
- 保留高检索价值关键词：工具名、模块名、卡片号、错误类型、目标动作。
- 避免泛化标题，如 `coding-help`、`debug-session`。
- 避免日期、emoji、空格、标点、长中文句子和敏感信息。

示例：

| 用户首轮意图 | 推荐标题 |
|---|---|
| 写一个 MGIT skill | `add-mgit-skill` |
| 自动给 Claude Code 会话 rename | `auto-rename-claude-sessions` |
| 修 FEEDADS-21199 分支迁移 | `migrate-feedads-21199-branch` |
| 排查 HTML 报告样式 | `fix-html-report-style` |
| 生成 CTS 验证用例 | `generate-cts-cases` |

## Hook 脚本模板

建议创建脚本，例如：

```text
/Users/markz/.claude/hooks/session-title.py
```

脚本示例：

```python
#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

STOPWORDS = {
    "a", "an", "the", "to", "for", "of", "in", "on", "and", "or", "with",
    "this", "that", "current", "please", "help", "me", "can", "you",
    "一下", "一个", "这个", "当前", "帮我", "能不能", "可以", "怎么"
}

ALIASES = [
    (r"\bmgit\b|多仓库", "mgit"),
    (r"claude\s*code|会话|对话|session|rename|重命名|命名", "claude-session"),
    (r"skill|技能", "skill"),
    (r"hook|hooks|钩子", "hook"),
    (r"html", "html"),
    (r"cts", "cts"),
]

def slugify(text):
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"https?://\S+", " ", text)
    text = text.lower()

    tokens = []
    for pattern, token in ALIASES:
        if re.search(pattern, text, flags=re.I) and token not in tokens:
            tokens.extend(token.split("-"))

    ticket_tokens = re.findall(r"[a-z]+-\d+", text, flags=re.I)
    tokens.extend(t.lower() for t in ticket_tokens)

    words = re.findall(r"[a-z][a-z0-9]+|\d+", text)
    for word in words:
        if word not in STOPWORDS and word not in tokens:
            tokens.append(word)
        if len(tokens) >= 6:
            break

    if not tokens:
        tokens = ["claude", "session"]

    slug = "-".join(tokens[:6])
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:60].strip("-") or "claude-session"

def count_user_prompts(transcript_path):
    if not transcript_path:
        return 0
    path = Path(transcript_path)
    if not path.exists():
        return 0
    count = 0
    try:
        for line in path.read_text(errors="ignore").splitlines():
            try:
                item = json.loads(line)
            except Exception:
                continue
            if item.get("type") == "user" or item.get("role") == "user":
                count += 1
    except Exception:
        return 0
    return count

try:
    payload = json.load(sys.stdin)
    prompt = payload.get("prompt", "")
    transcript_path = payload.get("transcript_path", "")

    # 只在会话早期自动命名，避免后续每轮都把标题改掉。
    if count_user_prompts(transcript_path) > 1:
        print("{}")
        raise SystemExit(0)

    title = slugify(prompt)
    print(json.dumps({"sessionTitle": title}, ensure_ascii=False))
except Exception:
    # hook 失败不能影响用户正常提问。
    print("{}")
```

## settings.json 配置

推荐使用 `update-config` skill 或手动编辑 `~/.claude/settings.json`，把脚本挂到 `UserPromptSubmit`。

示例：

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /Users/markz/.claude/hooks/session-title.py",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

如果 settings 里已经有 `UserPromptSubmit`，追加一个 hook，不要覆盖原配置。

## 手动命名当前会话

如果用户只想当场 rename 当前会话：

1. 从当前对话首轮用户请求和后续纠正中生成标题。
2. 推荐 1 个主标题，必要时给 2 到 3 个备选。
3. 优先使用官方支持的会话标题机制；如果当前环境没有直接命令可用，再考虑修改本地 session 元数据。

手动标题示例：

```markdown
建议命名为 `auto-rename-claude-sessions`。
依据：这次会话主要是在设计 Claude Code 会话自动命名 hook。
```

如果必须改本地元数据，先确认目标 session 文件，只修改 `name` 字段；不要改 `sessionId`、`cwd`、`startedAt`、`updatedAt`、`status`，也不要批量修改多个 session。

## 风险和注意事项

- 不要从 hook 里调用 Claude，容易变慢、递归或不稳定。
- hook stdout 必须是干净 JSON；日志写 stderr 或不写。
- hook 会阻塞用户 prompt 处理，脚本超时时间建议 5 秒以内。
- 不要上传 prompt 或 transcript 到外部服务。
- 不要直接删除或重写 `~/.claude/history.jsonl`、`~/.claude/projects/*.jsonl`。
- 自动命名应只在会话早期执行，避免后续补充问题把原标题覆盖掉。

## 回答用户时

如果用户问“能不能自动”：明确回答可以，推荐 `UserPromptSubmit` hook 返回 `sessionTitle`。

如果用户要你配置：先检查现有 `~/.claude/settings.json`，保留已有 hook，只追加 session title hook 和脚本。

如果用户要你只写 skill：只修改插件仓库中的 `skills/session-rename/SKILL.md`、`CHANGELOG.md`、版本记录，不触碰用户级 settings。
