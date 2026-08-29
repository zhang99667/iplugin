---
name: codex-session-export
version: 0.1.0
tags: [codex-session-export, codex, session, transcript, markdown, export]
description: Codex CLI 会话导出助手。当用户说“导出会话”“导出 Codex 聊天记录”“保存当前 Codex 对话”或要求把 Codex session、thread、codex exec 任务保存为 Markdown 时触发；当前仅解析 Codex CLI 本地 rollout JSONL 与 codex exec JSONL，不支持其他 Agent 的会话格式。
---

# Codex Session Export

只导出 Codex CLI 会话。即使由其他 Agent 宿主加载本 Skill，也不要把它描述为通用
Agent 会话导出器；Claude Code、Cursor 等工具的会话格式需要各自的适配器。

从这个 Skill 目录运行确定性导出脚本：

```bash
python3 scripts/export_session.py current
```

使用 `current` 导出当前 thread，使用 `latest` 导出最近更新的持久化 thread，
使用明确的 Session ID 精确选择，或传入保存下来的 `codex exec --json` JSONL
文件。用户指定输出目录时传 `--output-dir`；JSON 事件流缺少原始 prompt 时传
`--user-message`。只有用户明确要求工具详情时才传 `--include-tools`，因为参数
和输出可能包含项目数据。

本地找不到持久化 JSONL 时，明确说明无法导出。云端任务以及使用 `--ephemeral`
且没有保存 `codex exec --json` 输出的任务不在支持范围内。

命令成功后向用户报告生成的 Markdown 路径。
