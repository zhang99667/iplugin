---
name: local-session-archive
version: 0.1.0
tags: [session, archive, local, backup, codex, claude]
description: 本地 session 归档助手。当用户要求备份、同步、归档、恢复或迁移本机 Codex / Claude session，并明确希望“存在本地”“本地备份”“类似硅碳双键但不上传如流/知识库”时触发；它使用本仓库脚本把 JSONL session 离线复制到本机归档目录并支持列出、状态查看和恢复。
user_invocable: true
---

# 本地 Session 归档

把本机 Codex 和 Claude 的 JSONL session 复制到本机归档目录，提供离线备份、列出、状态查看和恢复能力。这个 skill 是“硅碳双键”的本地版：不调用如流、不上传知识库、不处理 ugate token。

## 工具入口

使用仓库脚本：

```bash
python3 scripts/local_session_archive.py <command>
```

默认归档目录：

```plain
~/.local/share/iplugin/session-archive
```

可以用环境变量或参数覆盖：

```bash
IPPLUGIN_SESSION_ARCHIVE_DIR=/path/to/archive python3 scripts/local_session_archive.py sync
python3 scripts/local_session_archive.py --archive-root /path/to/archive sync
```

## 触发边界

### 适用

- 用户希望把 Codex / Claude 对话 session 本地备份、本地同步、本地归档。
- 用户提到“类似硅碳双键”“session 自动备份”“存在本地”“不上传如流”“不走 KU/知识库”。
- 用户要列出已归档 session、查看归档状态、从本地归档恢复某个 session 文件。

### 不适用

- 用户希望同步到如流、KU、知识库、云端或跨机器共享；这类应使用对应 KU/如流工具或重新确认目标。
- 用户只是要重命名当前会话；使用 `session-rename`。
- 用户只问 Codex / Claude session 文件在哪里，不需要实际备份或恢复时，直接回答路径即可。

### 需要确认

- 恢复到原始 session 路径或覆盖已有文件前，必须先确认；脚本默认拒绝覆盖，只有用户明确同意后才使用 `--overwrite` 或 `--to-source`。
- 用户没有说明是否要后台持续同步时，默认只执行一次 `sync`，不要擅自启动长期 `watch`。

## 常用命令

一次性同步所有可发现的 Codex / Claude session：

```bash
python3 scripts/local_session_archive.py sync
```

只同步 Codex：

```bash
python3 scripts/local_session_archive.py sync --source codex
```

前台持续同步：

```bash
python3 scripts/local_session_archive.py watch --interval 60
```

查看状态：

```bash
python3 scripts/local_session_archive.py status
```

列出最近归档：

```bash
python3 scripts/local_session_archive.py list --limit 20
```

恢复到默认 `restored/` 目录：

```bash
python3 scripts/local_session_archive.py restore --id <session-id>
```

恢复到指定路径：

```bash
python3 scripts/local_session_archive.py restore --id <session-id> --target /path/to/session.jsonl
```

## 输出契约

- `sync` 输出 JSON，包含 `archive_root`、`discovered`、`copied`、`skipped`。
- `status` 输出 JSON，包含归档目录、索引路径和各来源计数。
- `list` 默认输出简表；需要机器可读结果时加 `--json`。
- `restore` 输出 JSON，包含恢复来源、目标路径、source 和 session id。

## 实现原则

- 完全本地：不联网、不上传、不读取 KU token。
- 幂等同步：同一个源文件 SHA256 未变化时跳过。
- 保留索引：每次复制都会追加 `index.jsonl`，用于 list 和 restore。
- 默认不覆盖：恢复时目标存在则失败，除非用户明确要求 `--overwrite`。
- 保持简单：不内置 launchd、cron 或后台 daemon；需要常驻时先用 `watch` 前台验证。
