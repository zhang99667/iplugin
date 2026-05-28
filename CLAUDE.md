# iPlugin 维护指南

这是一个 Claude Code Plugin 仓库，同时通过 `.codex-plugin/plugin.json` 兼容 Codex。当你在这个目录下工作时，遵循以下规则。

## 目录约定

- `.claude-plugin/plugin.json` — Claude Code 插件 manifest
- `.codex-plugin/plugin.json` — Codex 插件 manifest
- `skills/<name>/SKILL.md` — 技能定义，两边共用，目录名必须与 `SKILL.md` 中的 `name` 字段一致
- `commands/<name>.md` — slash command 入口，优先调用 `skills/` 中的通用能力，不承载大段重复逻辑
- `versions/vX.Y.Z.md` — 每个版本的规划和决策记录
- `scripts/` — 共享脚本（需要确定性执行的代码）
- `hooks/` — 全局钩子（横切关注点）

## 兼容原则

- `skills/` 是唯一真源，不为 Claude Code 和 Codex 分别复制 skill
- `CLAUDE.md` 与 `AGENTS.md` 是同源维护指南；修改其中一个时必须同步另一个，除非差异有明确平台原因并在文中说明
- 插件级信息变更时，同时检查 `.claude-plugin/plugin.json` 和 `.codex-plugin/plugin.json`
- 版本号、描述、关键词应尽量在两个 manifest 中保持一致
- Codex 插件刷新使用 `codex plugin marketplace upgrade iplugin`
- 如果未来加入 hooks，Claude Code 和 Codex 的 hooks 配置需要分别验证；不要默认认为两边 1:1 兼容

## Skill 准入标准

- 必须是**通用、可复用**的能力，不能是一次性任务或特定项目的补丁
- 不确定时，先问"换个项目、换个语言、换个人，这个 skill 还能用吗？"

## 添加 Skill

1. `mkdir -p skills/<kebab-case-name>`
2. 编写 `SKILL.md`，YAML frontmatter 必须包含：`name`、`version`、`description`、`tags`
3. `description` 用第三人称，包含具体触发短语
4. 更新 `.claude-plugin/plugin.json` 和 `.codex-plugin/plugin.json` 的描述或关键词（如有必要）
5. 更新 `CHANGELOG.md`（Add 条目）
6. 记录 `versions/vX.Y.Z.md`
7. `git commit`

## 添加 Command

1. `mkdir -p commands`
2. 编写 `commands/<command-name>.md`，YAML frontmatter 至少包含 `description`
3. 命令正文只做参数解析和编排，通用能力沉淀到 `skills/<name>/SKILL.md`
4. 如新增用户可见能力，更新 README、CHANGELOG 和 `versions/vX.Y.Z.md`
5. 需要改变插件定位时，同步检查 `.claude-plugin/plugin.json` 与 `.codex-plugin/plugin.json`

## 版本号

- 插件级版本同时维护在 `.claude-plugin/plugin.json` 和 `.codex-plugin/plugin.json` 中
- 每个 skill 在各自 `SKILL.md` frontmatter 中有独立 `version`
- 遵循 SemVer：Patch（指令优化）、Minor（新增/改名 skill）、Major（删除/breaking change）
- 每次变更必须在 `versions/` 下记录对应的版本规划文档

## 版本规划文档

每次版本变更需要在 `versions/` 下记录。格式取决于内容量：

- **内容少（单个文件能写完）**：写成 `versions/vX.Y.Z.md`，包含这次改了什么、为什么这样改、架构决策
- **内容多（多个文档/图表/方案对比）**：建文件夹 `versions/vX.Y.Z/`，内部可自由组织多个 `.md` 文件

一个典型的 vX.Y.Z.md 应包含：目标、变更清单、架构决策、排除项及原因。

## 提交前检查

- `.claude-plugin/plugin.json` 与 `.codex-plugin/plugin.json` 的插件级版本、描述、关键词已同步
- CHANGELOG.md 已更新
- versions/vX.Y.Z.md 已写好（如果是新版本）
- `skills/*/SKILL.md` 的 `name` 与目录名一致
- `commands/*.md` 只保留轻量编排逻辑，未复制大段 skill 正文
- 每次完成文件改动并做完必要校验后，必须通过 `/ask-user-question` 询问用户是否要把本次改动提交；用户确认前不要主动执行 `git commit`
