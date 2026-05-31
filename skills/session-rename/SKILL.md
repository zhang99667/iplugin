---
name: session-rename
version: 0.1.2
tags: [claude-code, session, hooks, productivity]
description: Claude Code 会话命名助手，仅当用户明确要求重命名当前会话、给当前对话起标题、自动命名 Claude Code 会话，或配置 UserPromptSubmit sessionTitle hook 时触发。不要因命名分支、PR、文件、项目或 Codex 对话触发。仅适用于 Claude Code 环境。
---

# Claude Code 会话命名助手

目标：让 Claude Code 会话自动获得短而可检索的标题，方便用户后续从会话列表里找回上下文。

优先方案是配置 `UserPromptSubmit` hook，在用户每次提交 prompt 时由本地脚本返回 `sessionTitle`。这是官方支持的会话标题设置方式，比直接修改 `~/.claude/sessions/*.json` 更安全。

## 触发边界

### 适用

- 用户要求"自动重命名会话""以后都帮我给会话命名"。
- 用户说找不到会话，因为会话没有 rename/title。
- 用户要求"根据第一轮对话给当前会话起名"。
- 用户询问能否用 hook 或其他方式自动更新会话标题。

### 不适用

不要用于给代码分支、PR、commit、文件、业务项目或普通文档改名。非 Claude Code 环境里不要建议编辑 `.claude` 配置。

### 需要确认

如果当前平台不是 Claude Code，先说明该技能只适用于 Claude Code；如果用户只是要一个标题建议，可以只给标题，不修改本地配置。

## 核心工作流

**配置自动命名（推荐）：**

1. 使用 `update-config` skill 或手动编辑 `~/.claude/settings.json`。
2. 把 `UserPromptSubmit` hook 指向 `~/.claude/hooks/session-title.py`。
3. 脚本读取 stdin JSON，提取 `prompt`，生成英文 kebab-case 标题，输出 `{"sessionTitle":"xxx"}`。
4. 只在会话早期（第 1 轮）命名，避免后续补充问题覆盖原标题。

**手动命名当前会话：**

1. 从当前对话首轮用户请求和后续纠正中生成标题。
2. 推荐 1 个主标题，必要时给 2 到 3 个备选。

## 标题规则

- 英文 kebab-case，3 到 6 个词，约 20 到 50 个字符。
- 保留高检索价值关键词：工具名、模块名、卡片号、错误类型、目标动作。
- 避免泛化标题（如 `coding-help`）、日期、emoji、空格、标点、敏感信息。

## Progressive Disclosure

需要完整 hook 脚本实现、settings.json 配置示例或标题示例表时，读取：

- `references/hook-script.md`：完整 Python 脚本、settings.json 配置、标题示例、风险注意事项

## 回答用户时

如果用户问"能不能自动"：明确回答可以，推荐 `UserPromptSubmit` hook 返回 `sessionTitle`。

如果用户要你配置：先检查现有 `~/.claude/settings.json`，保留已有 hook，只追加 session title hook 和脚本。

如果用户要你只写 skill：只修改插件仓库中的 `skills/session-rename/SKILL.md`、`CHANGELOG.md`、版本记录，不触碰用户级 settings。

如果必须改本地元数据，先确认目标 session 文件，只修改 `name` 字段；不要改 `sessionId`、`cwd`、`startedAt`、`updatedAt`、`status`，也不要批量修改多个 session。
