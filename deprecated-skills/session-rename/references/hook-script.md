# session-rename Hook 脚本参考

## Hook 脚本完整实现

创建脚本位置：`~/.claude/hooks/session-title.py`

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

## settings.json 配置示例

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/session-title.py",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

如果 settings 里已经有 `UserPromptSubmit`，追加一个 hook，不要覆盖原配置。

## 标题示例

| 用户首轮意图 | 推荐标题 |
|---|---|
| 写一个 MGIT skill | `add-mgit-skill` |
| 自动给 Claude Code 会话 rename | `auto-rename-claude-sessions` |
| 修 FEEDADS-21199 分支迁移 | `migrate-feedads-21199-branch` |
| 排查 HTML 报告样式 | `fix-html-report-style` |
| 生成 CTS 验证用例 | `generate-cts-cases` |

## 风险和注意事项

- 不要从 hook 里调用 Claude，容易变慢、递归或不稳定。
- hook stdout 必须是干净 JSON；日志写 stderr 或不写。
- hook 会阻塞用户 prompt 处理，脚本超时时间建议 5 秒以内。
- 不要上传 prompt 或 transcript 到外部服务。
- 不要直接删除或重写 `~/.claude/history.jsonl`、`~/.claude/projects/*.jsonl`。
- 自动命名应只在会话早期执行，避免后续补充问题把原标题覆盖掉。
