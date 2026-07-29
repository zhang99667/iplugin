# iPlugin

toolbox — 代码阅读、爱迪生答题题库、复杂任务委派、结构化询问、Android mock 自测验收、组件化 HTML 报告生成、图片/视频证据预览、可编辑且可内嵌交接的离线评论模式、SVG 技术图生成、HTML 转 Markdown、联网精选、通用图片生成、SQL 实验替换、商业 SQL 写作、DataPilot SQL 跑数结果闭环、商业 AB 透视表生成、项目/需求总结、Obsidian 分模式写作与编辑审校、iCafe 交付归档、矩阵差异化标记、Karpathy 编码准则、MGIT/EasyBox 多仓辅助、xbuild 源码自动补开的个人研发工作流通用插件。

## 仓库顶层目录结构

以下结构描述 Git 仓库中跟踪的顶层目录和关键文件；本地缓存、IDE 配置、空目录不列入。

```
iplugin/
├── .claude-plugin/
│   └── plugin.json
├── .codex-plugin/
│   └── plugin.json
├── skills/
│   └── <name>/             # 当前启用 skill；包含 SKILL.md，可按需带 references/、scripts/ 或 assets/
├── deprecated-skills/      # 已退役 skill 的历史快照，不参与插件发现和能力注册
├── hooks/                  # 全局横切 hooks，区分 Claude / Codex 配置
├── git-hooks/              # 可版本化 Git hooks，启用后在 push 前做版本防撞检查
├── scripts/                # 共享脚本和提交前校验
├── docs/                   # 跨版本架构设计与较大改造留档
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
| `code-reading` | 逐步详解代码执行链路，追踪创建→初始化→注册→触发→分发全过程；EasyBox/xbuild 目标源码缺失时联动自动补开 | "带我读代码"、"从入口到触发完整讲一遍" |
| `aidisheng-xueba` | 按已背题库匹配爱迪生考试题干和选项语义，快速输出单选/多选答案 | "爱迪生学霸"、"爱迪生考试这题选什么"、"帮我答爱迪生题库" |
| `ask-user-question` | 把阻塞性决策、提交前确认、风险操作确认整理成结构化选择题，交给 AskUserQuestion / request_user_input | `/ask-user-question 这个 UI 改动应该怎么做`、"提交前让我确认" |
| `android-mock` | 按 Android mock 文档和测试用例逐 case 执行真机验收，区分多条链路，沉淀截图/录屏/logcat/mockserver 证据并生成验收报告 | "帮我自测这个 Android mock 方案"、"跑完这些用例并补截图证据"、"生成链路分离的验收报告" |
| `best-of-web` | 仅通过 `/best-of-web` 命令触发；联网搜索并按来源质量分层核验公开资料，再综合成可引用、可执行的回答 | `/best-of-web 结合互联网上最优秀的内容梳理这个主题` |
| `delegated-search` | 在复杂排查、找全调用链、影响面分析、跨模块实现或高输出验证前先做委派判断，将可独立调查、实现或验证的子任务拆给 explorer/worker/verifier，主线程负责整合与交付 | "帮我找全相关实现"、"这个链路可能在哪里断"、"先拆子 Agent 并行查一下"、"这个复杂任务看看能不能拆给 worker 做" |
| `html-report` | 生成独立单文件 HTML 报告；内部用注册表和统一装配器组合表格、代码、每文件 Diff、短标签 IDE 跳转、图片点击放大、目录、Tabs、排序和多版本 Review Workspace，并做组件级校验；可注入离线评论模式，把 `AgentQuestionPack` 内嵌回 HTML 交给 Agent 更新并导出无批注发布版 | "整理成 HTML 报告"、"复用两方/三方 Review Workspace"、"给这个 HTML 加评论模式"、"按 HTML 内嵌评论更新报告"、`/html-report` |
| `svg-tech-diagram` | 为技术长文、HTML 报告、架构说明和代码链路生成朴素清晰的 SVG 技术图，按内容包围盒自适应画布，并通过几何/像素闸门和渲染 PNG 自审保证箭头、文字和布局可读 | "画 SVG 图"、"配张架构图"、"生成技术示意图"、"公众号配图" |
| `html2md` | 用标准库脚本把本地 HTML、`file://` 页面或粘贴的 HTML 内容转换成 Markdown | "HTML 转 MD"、"file:///... 输出成 md"、"把这个 HTML 报告转 Markdown" |
| `generate-image` | 生成图片并按需求保存到本地；普通出图可用平台内置能力，明确指定 `gptimage` / `gptimg2` / `banana2` 等接口链路时必须走通用 API 客户端，默认并发生成 3 张候选图并视觉筛选只保留最佳图，路由词不会进入最终图片 prompt，API key 首次提供后保存到本地私有缓存复用 | "生成图片"、"banana2 出图"、"用 gptimg2 保存这张图" |
| `sql-exp-replace` | 用确定性脚本批量替换 SQL 中的实验号和日期范围 | "把实验号改成 162160，日期改成 0508 到 0513" |
| `commercial-sql-writer` | 编写、改写和检查商业/NAD 广告分析 SQL，按场景选择表、字段、指标口径和模板，覆盖落地页性能/抵达率口径 | "帮我写一个展点消大盘 SQL"、"检查这个商业 SQL 的 join 和转化口径" |
| `datapilot-sql-runner` | 在 DataPilot 上提交单条或多条 SQL，默认使用 MCP 完成提交、查状态、等待下载和结果下载；结果字段匹配时联动商业 AB 透视表 skill 直接产出 xlsx，Chrome 只作为页面专属设置或 MCP 不可用时的兜底 | "DataPilot 跑一下这个 SQL 并下载结果"、"跑完这些 SQL 直接生成透视表" |
| `nad-acx-pivot-table` | 生成商业 AB 实验数据分析透视表 xlsx，支持 CSV/TXT/XLSX 合并、字段别名映射、原生 Excel 透视表和相对差指标 | "生成商业 AB 实验透视表"、"合并最近 3 个 csv/txt 生成透视表" |
| `project-summary` | 整理项目、需求、Bug 修复或阶段性工作的总结与复盘 | "总结一下这个需求"、"把这次做的事整理成项目总结" |
| `obsidian` | 按工作模式与文档类型组织证据和写作合同；指定参考文时强制提取风格画像，完整指南检查概念依赖，并执行结构、文风两轮全篇审查和反馈回归 | "写到 Obsidian"、"参考这篇文章写完整技术指南"、"修改这篇旧笔记并检查全文" |
| `icafe-delivery-archive` | 查询 iCafe 需求并归档需求描述、技术详设和总结材料 | "把这个详设归档到需求交付"、"根据文档推断是哪个卡片" |
| `lite-diff-marker` | 给 Android 矩阵差异化改动补齐 @LiteAdd/@LiteModified/@LiteDelete/@BaseSplit 标记 | "给这次改动添加差异化标记" |
| `karpathy-guidelines` | 写代码、重构和 review 时应用简洁、克制、可验证的工程准则 | "按 Karpathy 准则帮我改这段代码" |
| `mgit` | 百度 MGIT 多仓状态、分支、仓库范围和中间态诊断；执行前预检 Ruby/gem/colored2 等启动依赖；支持结合 EasyBox/xbuild `overlay` / `local` 配置判断开发分支上车和 master 合入时的源码模式范围；多仓写操作需确认 | "整体看一下这套工程状态"、"根据这些改动更新 EasyBox overlay/local" |
| `xbuild-open-source` | 反查 EasyBox/xbuild 模块映射；显式要求开源码或其他代码任务发现源码缺失时，自动最小补个人 local 配置、精确同步唯一目标仓并继续原任务 | "帮我打开这个 xbuild 仓库源码模式"、"带我读这段代码，缺源码就自动开" |

## Deprecated Skills

退役 skill 已移出插件扫描目录，仅保留在 [`deprecated-skills/`](./deprecated-skills/) 供历史追溯。目前归档：

| 名称 | 退役版本 | 原因 |
|------|---------|------|
| `session-rename` | `0.22.11` | Codex 与 Claude telemetry 均无实际任务命中，且只适用于 Claude Code |

## Commands

当前没有独立 `commands/*.md` 入口。以下 slash command 触发语义已整合进同名 skill，输入命令名即可触发对应 skill：

| 命令 | 对应 skill |
|------|-----------|
| `/ask-user-question` | `ask-user-question` |
| `/best-of-web` | `best-of-web` |
| `/html-report` | `html-report` |

## 安装

下面是 Claude Code 的本地市场安装示例。Codex 侧复用同一份活跃 `skills/`、`hooks/` 与 `.codex-plugin/plugin.json`；`deprecated-skills/` 不参与注册。

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

`skills/` 只放当前启用能力。确认不再维护的 skill 整体移动到 `deprecated-skills/<name>/`，补齐退役元数据和归档说明，并从 manifest 与活跃清单移除；不要把废弃目录继续留在 `skills/` 下。

## 提交前校验

改动插件结构、manifest、skills、commands、README、CHANGELOG 或版本记录后，运行：

```bash
python3 scripts/validate-plugin.py
```

校验会检查 manifest JSON 合法性、两个 manifest 公共字段一致性、活跃 skill 目录名与 frontmatter name 一致性、README 与实际 skills 清单一致性、废弃 skill 隔离和退役元数据、CHANGELOG 版本记录完整性，以及 command 引用的 skill 是否存在。

## Push 前版本防撞

本仓库提供版本化的 pre-push hook。每个本地 clone 需要手动启用一次，因为 `.git/config` 不会进入 Git 提交；启用后后续 `git push` 会自动运行检查。在仓库根目录执行：

```bash
git config core.hooksPath git-hooks
```

也可以在提交后、push 前手动预跑同一套检查：

```bash
python3 scripts/pre_push_version_check.py
```

检查会在 push 前 `git fetch --prune <remote>` 获取远端状态；如果本地没有包含远端最新提交、本地 manifest 版本没有大于远端版本，或远端已经存在同版本 `CHANGELOG` / `versions` 记录，就拒绝 push。脚本不会在 hook 中自动 merge 或 rebase；被拦截后先执行 `git pull --rebase` 或 `git pull --ff-only`，再重新选择版本号。
