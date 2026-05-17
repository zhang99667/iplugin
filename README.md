# iPlugin

toolbox — 代码阅读、HTML 报告生成、SQL 实验替换的个人专属 Claude Code Plugin。

## 目录结构

```
iplugin/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   ├── code-reading/       # 带我读代码，追踪执行链路
│   ├── html-report/        # 生成美观的独立 HTML 工程报告
│   └── sql-exp-replace/    # SQL 实验号与日期批量替换
├── versions/               # 版本规划与决策文档
├── scripts/                # 共享脚本（按需添加）
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
| `html-report` | 生成浅灰背景、白色卡片的独立 HTML 报告，输出到桌面 | "整理成 HTML 报告"、"/htmlreport" |
| `sql-exp-replace` | 批量替换 SQL 中的实验号和日期范围 | "把实验号改成 162160，日期改成 0508 到 0513" |

## 安装

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