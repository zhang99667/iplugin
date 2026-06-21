# iPlugin

toolbox — 代码阅读、爱迪生答题题库、广域检索委派、结构化询问、HTML 报告生成与离线批注审核、SVG 技术图生成、HTML 转 Markdown、联网精选、SQL 实验替换、商业 SQL 写作、DataPilot SQL 跑数、商业 AB 透视表生成、项目/需求总结、Obsidian 笔记写作、iCafe 交付归档、矩阵差异化标记、Karpathy 编码准则、MGIT/EasyBox 多仓辅助的个人研发工作流通用插件。

## 仓库顶层目录结构

以下结构描述 Git 仓库中跟踪的顶层目录和关键文件；本地缓存、IDE 配置、空目录不列入。

```
iplugin/
├── .claude-plugin/
│   └── plugin.json
├── .codex-plugin/
│   └── plugin.json
├── skills/
│   └── <name>/             # 每个 skill 目录包含 SKILL.md，可按需带 references/ 或 scripts/
├── hooks/                  # 全局横切 hooks，区分 Claude / Codex 配置
├── scripts/                # 共享脚本和提交前校验
├── tools/                  # 独立工具子项目，不自动进入插件 manifest
│   ├── remote-android-build/
│   └── z-agent/
├── versions/               # 插件版本规划与决策文档
├── CLAUDE.md               # 插件维护指南（Claude 在此目录下生效）
├── AGENTS.md               # 插件维护指南（Codex 在此目录下生效）
├── README.md
├── CHANGELOG.md
└── .gitignore
```

## Skills

| 名称 | 用途 | 触发示例 |
|------|------|---------|
| `code-reading` | 逐步详解代码执行链路，追踪创建→初始化→注册→触发→分发全过程 | "带我读代码"、"从入口到触发完整讲一遍" |
| `aidisheng-xueba` | 按已背题库匹配爱迪生考试题干和选项语义，快速输出单选/多选答案 | "爱迪生学霸"、"爱迪生考试这题选什么"、"帮我答爱迪生题库" |
| `ask-user-question` | 把阻塞性决策、提交前确认、风险操作确认整理成结构化选择题，交给 AskUserQuestion / request_user_input | `/ask-user-question 这个 UI 改动应该怎么做`、"提交前让我确认" |
| `best-of-web` | 仅通过 `/best-of-web` 命令触发；联网搜索并按来源质量分层核验公开资料，再综合成可引用、可执行的回答 | `/best-of-web 结合互联网上最优秀的内容梳理这个主题` |
| `delegated-search` | 将发散搜索、证据收集、多来源核验和高输出操作前置判断拆给 explorer/subagent，主线程负责判断与整合 | "帮我找全相关实现"、"这个链路可能在哪里断"、"查一下这些字段分别从哪来"、"先判断能不能拆给子 Agent" |
| `html-report` | 生成独立单文件 HTML 报告；正式文档加抬头，代码块离线高亮，复杂技术图可调用 `svg-tech-diagram` 生成内联 SVG，可按需注入离线批注审核模式并导出 Markdown/JSON 提问包和发布版 HTML | "整理成 HTML 报告"、"给这个 HTML 加批注审核模式"、`/html-report` |
| `svg-tech-diagram` | 为技术长文、HTML 报告、架构说明和代码链路生成朴素清晰的 SVG 技术图，并通过渲染 PNG 后自审迭代保证箭头、文字和布局可读 | "画 SVG 图"、"配张架构图"、"生成技术示意图"、"公众号配图" |
| `html2md` | 用标准库脚本把本地 HTML、`file://` 页面或粘贴的 HTML 内容转换成 Markdown | "HTML 转 MD"、"file:///... 输出成 md"、"把这个 HTML 报告转 Markdown" |
| `sql-exp-replace` | 用确定性脚本批量替换 SQL 中的实验号和日期范围 | "把实验号改成 162160，日期改成 0508 到 0513" |
| `commercial-sql-writer` | 编写、改写和检查商业/NAD 广告分析 SQL，按场景选择表、字段、指标口径和模板 | "帮我写一个展点消大盘 SQL"、"检查这个商业 SQL 的 join 和转化口径" |
| `datapilot-sql-runner` | 在 DataPilot 上提交单条或多条 SQL，处理 Chrome 登录态、Monaco 编辑器粘贴、任务 ID 回收和排队/执行状态汇报 | "DataPilot 跑一下这个 SQL"、"把这些 .sql 提交到 datapilot 并回收任务 ID" |
| `nad-acx-pivot-table` | 生成商业 AB 实验数据分析透视表 xlsx，支持 CSV/TXT/XLSX 合并、字段别名映射、原生 Excel 透视表和相对差指标 | "生成商业 AB 实验透视表"、"合并最近 3 个 csv/txt 生成透视表" |
| `project-summary` | 整理项目、需求、Bug 修复或阶段性工作的总结与复盘 | "总结一下这个需求"、"把这次做的事整理成项目总结" |
| `obsidian` | 写入 Obsidian Vault 时应用统一 Markdown 排版、标题层级、引用块、双链规范，并按清晰度选择 Mermaid / ASCII / SVG / 图像生成等示意图表达 | "写到 Obsidian"、"记到笔记里"、"加到 vault 里" |
| `icafe-delivery-archive` | 查询 iCafe 需求并归档需求描述、技术详设和总结材料 | "把这个详设归档到需求交付"、"根据文档推断是哪个卡片" |
| `lite-diff-marker` | 给 Android 矩阵差异化改动补齐 @LiteAdd/@LiteModified/@LiteDelete/@BaseSplit 标记 | "给这次改动添加差异化标记" |
| `karpathy-guidelines` | 写代码、重构和 review 时应用简洁、克制、可验证的工程准则 | "按 Karpathy 准则帮我改这段代码" |
| `mgit` | 百度 MGIT 多仓状态、分支、仓库范围和中间态诊断；执行前预检 Ruby/gem/colored2 等启动依赖；支持结合 EasyBox/xbuild `overlay` / `local` 配置判断开发分支上车和 master 合入时的源码模式范围；多仓写操作需确认 | "整体看一下这套工程状态"、"根据这些改动更新 EasyBox overlay/local" |
| `session-rename` | 为 Claude Code 会话生成可检索标题 | "重命名当前会话" |

## Commands

当前没有独立 `commands/*.md` 入口。以下 slash command 触发语义已整合进同名 skill，输入命令名即可触发对应 skill：

| 命令 | 对应 skill |
|------|-----------|
| `/ask-user-question` | `ask-user-question` |
| `/best-of-web` | `best-of-web` |
| `/html-report` | `html-report` |

## 安装

下面是 Claude Code 的本地市场安装示例。Codex 侧复用同一份 `skills/`、`hooks/` 与 `.codex-plugin/plugin.json`。

1. 创建市场目录并软链接 git 仓库：

```bash
mkdir -p ~/.claude/plugins/marketplaces/iplugin
ln -s /Users/markz/code/tools/iplugin ~/.claude/plugins/marketplaces/iplugin/iplugin
```

2. 在 `~/.claude/settings.json` 中注册市场并启用：

```json
{
  "extraKnownMarketplaces": {
    "iplugin": {
      "source": {
        "source": "directory",
        "path": "/Users/markz/.claude/plugins/marketplaces/iplugin"
      }
    }
  },
  "enabledPlugins": {
    "iplugin@iplugin": true
  }
}
```

软链接指向 git 仓库，修改 SKILL.md 后下次对话自动生效。

Codex 侧刷新本地插件：

```bash
codex plugin marketplace upgrade iplugin
```

Claude Code 会默认扫描 `hooks/hooks.json`，其中使用 `${CLAUDE_PLUGIN_ROOT}` 和 `matcher: "Skill"`。Codex 启用插件后会通过 `.codex-plugin/plugin.json` 读取 `hooks/codex-hooks.json`，其中第一入口使用 `$HOME/.codex/hooks/iplugin-skill-telemetry.py` 稳定 wrapper，再转发到当前仓库或最新插件缓存里的 `hooks/skill-telemetry.py`，避免 session 继续引用已删除的版本化 `${PLUGIN_ROOT}` 缓存路径。首次启用或脚本变更后，在对应 CLI 中执行 `/hooks` 并 trust 该 hook。

Telemetry 默认日志：

- Claude Code: `~/.claude/skill-usage.jsonl`
- Codex: `~/.codex/skill-usage.jsonl`

可用 `IPPLUGIN_SKILL_USAGE_LOG` 覆盖日志路径。

## 添加新 Skill

```bash
mkdir -p skills/new-skill-name
# 编写 SKILL.md，包含 YAML frontmatter（name + version + description + tags）
# 长规则、模板和示例优先放到 skills/new-skill-name/references/
# git commit
# 自动生效
```

### Skill 准入标准

只纳入**通用、可复用**的能力。一次性任务脚本、特定项目/文件的补丁式 skill 不适合放在这里。

## 提交前校验

改动插件结构、manifest、skills、commands、README、CHANGELOG 或版本记录后，运行：

```bash
python3 scripts/validate-plugin.py
```

校验会检查 manifest JSON 合法性、两个 manifest 公共字段一致性、skill 目录名与 frontmatter name 一致性、README 与实际 skills 清单一致性、CHANGELOG 版本记录完整性，以及 command 引用的 skill 是否存在。
