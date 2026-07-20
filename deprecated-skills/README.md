# Deprecated Skills

本目录保存已从插件活跃能力中退役的 skill 快照。Codex manifest 只扫描 `./skills/`，Claude Code 也只把顶层 `skills/` 视为当前能力，因此这里的 `SKILL.md` 不会被注册或自动触发。

| 名称 | 退役版本 | 原因 | 替代方式 |
| --- | --- | --- | --- |
| `session-rename` | `0.22.11` | Codex 与 Claude telemetry 均无实际任务命中，且能力仅适用于 Claude Code 会话标题 | 需要标题时直接给出标题建议；需要自动化时按当时平台能力重新设计 |

## 归档约束

- 归档目录保留退役时的完整内容，包括 references、scripts（如有）和说明，用于追溯，不继续做功能迭代。
- 每个归档 `SKILL.md` 必须声明 `deprecated: true`、`deprecated_in` 和 `deprecated_reason`。
- 退役 skill 不得出现在 README 活跃 Skills 表、manifest 关键词、Codex 默认提示或 `skills/` 扫描目录中。
- 需要恢复时，不直接从本目录调用；先重新评估适用性和触发边界，再整体移回 `skills/<name>/` 并按仓库版本规则发布。
