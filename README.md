# iPlugin

toolbox — 代码阅读、广域检索委派、结构化询问、HTML 报告生成、SQL 实验替换、项目/需求总结、iCafe 交付归档、矩阵差异化标记、Karpathy 编码准则的个人研发工作流通用插件。

## 目录结构

```
iplugin/
├── .claude-plugin/
│   └── plugin.json
├── .codex-plugin/
│   └── plugin.json
├── skills/
│   ├── code-reading/       # 带我读代码，追踪执行链路
│   ├── ask-user-question/   # 手动结构化询问，把不确定点交给 AskUserQuestion
│   ├── delegated-search/   # 广域检索任务委派与证据收集
│   ├── html-report/        # 生成带内容类型判断的独立 HTML 工程报告
│   ├── sql-exp-replace/    # SQL 实验号与日期批量替换
│   ├── project-summary/    # 项目/需求总结整理
│   ├── icafe-delivery-archive/ # iCafe 需求交付材料归档
│   ├── lite-diff-marker/   # 矩阵产品差异化标记
│   ├── karpathy-guidelines/ # Karpathy 风格编码准则
│   ├── mgit/               # 百度 MGIT 多仓库管理
│   └── session-rename/     # Claude Code 会话自动命名
├── commands/               # slash command 入口
├── versions/               # 版本规划与决策文档
├── scripts/                # 共享脚本和提交前校验
├── hooks/                  # 全局横切 hooks（按需添加）
├── CLAUDE.md               # 插件维护指南（Claude 在此目录下生效）
├── README.md
├── CHANGELOG.md
└── .gitignore
```

## Skills

| 名称 | 用途 | 触发示例 |
|------|------|---------|
| `code-reading` | 逐步详解代码执行链路，追踪创建→初始化→注册→触发→分发全过程 | "带我读代码"、"梳理一下这个方法的调用链路" |
| `ask-user-question` | 手动把不确定点整理成结构化选择题，交给 AskUserQuestion / request_user_input | `/ask-user-question 这个 UI 改动应该怎么做` |
| `delegated-search` | 将发散搜索、证据收集、多来源核验任务拆给 explorer/subagent，主线程负责判断与整合 | "帮我找全相关实现"、"这个链路可能在哪里断"、"查一下这些字段分别从哪来" |
| `html-report` | 生成独立 HTML 报告；正式技术/业务文档会加文档抬头，普通对话整理保持轻量页面 | "整理成 HTML 报告"、"/htmlreport" |
| `sql-exp-replace` | 批量替换 SQL 中的实验号和日期范围 | "把实验号改成 162160，日期改成 0508 到 0513" |
| `project-summary` | 整理项目、需求、Bug 修复或阶段性工作的总结与复盘 | "总结一下这个需求"、"把这次做的事整理成项目总结" |
| `icafe-delivery-archive` | 查询 iCafe 需求并归档需求描述、技术详设和总结材料 | "把这个详设归档到需求交付"、"根据文档推断是哪个卡片" |
| `lite-diff-marker` | 给 Android 矩阵差异化改动补齐 @LiteAdd/@LiteModified/@LiteDelete/@BaseSplit 标记 | "给这次改动添加差异化标记" |
| `karpathy-guidelines` | 写代码、重构和 review 时应用简洁、克制、可验证的工程准则 | "按 Karpathy 准则帮我改这段代码" |
| `mgit` | 百度 MGIT 多仓库状态、同步、分支和批量操作辅助 | "看一下 mgit 多仓库状态" |
| `session-rename` | 为 Claude Code 会话生成可检索标题 | "重命名当前会话" |

## Commands

| 命令 | 用途 |
|------|------|
| `/ask-user-question` | 手动把当前不确定点交给结构化询问机制，让用户选择后再继续执行 |
| `/htmlreport` | 把当前回答、上一轮回答或提供的上下文整理成独立 HTML 报告 |

## 安装

下面是 Claude Code 的本地市场安装示例。Codex 侧复用同一份 `skills/` 与 `.codex-plugin/plugin.json`。

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

## 添加新 Skill

```bash
mkdir -p skills/new-skill-name
# 编写 SKILL.md，包含 YAML frontmatter（name + version + description + tags）
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
