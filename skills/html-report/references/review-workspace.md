# Review Workspace 组件

Review Workspace 用于在单文件 HTML 代码评审报告中审阅多个文件的 2 到 3 份完整源码快照。它复用“三方代码 Review”报告里的核心体验：文件导航、结论筛选、多版本并排、同步滚动、差异聚焦、参考行跳转、全文复制、IDE 打开和本地已审阅进度。

它是代码评审报告的按需增强组件，不是所有代码报告的默认结构。

## 什么时候使用

同时满足以下条件时使用：

- 用户明确希望复用 Workspace、审阅台、三方对比或多版本完整源码浏览。
- 需要在多个文件之间频繁切换。
- 每个文件有 2 到 3 个有意义的版本，例如 `基线 / master / 工作区`、`修改前 / 修改后`、`主版 / Lite / 修复后`。
- 只看聚焦 diff 不足以判断整文件关系、参考行上下文或差异化标记。

以下情况不要使用：

- 只有一个小 patch，标准 `.diff-card.diff-viewer` 已足够。
- 用户只要 Findings、风险结论或简短修复说明。
- 版本超过 3 个；先缩减成最有判断价值的 2 到 3 个版本。
- 完整源码会让报告异常膨胀，但用户并不需要全文审阅。

## 与标准 diff viewer 的分工

- Review Workspace 回答“这些文件在几个版本里整体长什么样、参考行在哪里、差异上下文是什么”。
- `.diff-card.diff-viewer` 回答“本次真实 patch 到底新增、删除或修改了什么”。
- Workspace 不能替代 Findings、测试缺口和真实 unified diff。代码评审报告仍应先给结论和问题，再放 Workspace；真实补丁仍用 `highlight_code.py --lang diff --diff-view`。

## 组件组成

生成报告时由脚本和统一装配器按需处理：

- `assets/components/code-block/style.css`：提供 `tok-*` 静态高亮颜色，由依赖自动带入。
- `assets/review-workspace/workspace.css`：提供 Workspace 布局、代码窗格、响应式和打印样式。
- `assets/review-workspace/workspace.js`：提供离线交互 runtime；通常由构建脚本自动内联。
- `scripts/build_review_workspace.py`：读取 JSON 规格和源码快照，输出安全的 HTML 组件片段。
- `scripts/assemble_report.py`：识别 `.review-workspace`，解析依赖并内联 Workspace 和基础组件样式。

不要手写大段 Workspace JS，也不要把示例报告里的业务字段、文件名、状态类型或 `localStorage` key 原样复制到新报告。

## 最短使用流程

1. 准备 2 到 3 份源码快照。工作区文件可直接引用；历史版本或其他分支先输出为临时文本文件。
2. 编写 Workspace JSON 规格，路径相对规格文件或使用绝对路径。
3. 运行：

   ```bash
   python3 skills/html-report/scripts/build_review_workspace.py workspace_spec.json -o workspace_fragment.html
   ```

4. 把生成片段插入代码评审报告的 Findings / 改动概览之后、真实补丁之前。
   - 三版本窗格希望尽量同时可见时，无目录页面可给 `<main>` 增加 `rw-layout-wide`。
   - 使用左侧目录时可给 `.layout-with-toc` 增加 `rw-layout-wide`；组件 CSS 只放宽这类报告，不改变普通报告宽度。
5. 完整报告写好后运行 `assemble_report.py`。注册表会自动加入 `base`、`interactions`、
   `file-location`、`code-block` 和 `review-workspace`；长报告出现目录结构时再自动加入 `toc`。

6. 如果一份报告有多个 Workspace，第一个片段保留 runtime，后续片段使用：

   ```bash
   python3 skills/html-report/scripts/build_review_workspace.py second_spec.json \
     --no-runtime -o second_workspace_fragment.html
   ```

7. 完成后运行：

   ```bash
   python3 skills/html-report/scripts/check_html_report.py report.html
   ```

## 规格格式

最小示例。这里的 `default_ide: "idea"` 来自 Android 技术方案上下文，与文件的
`language` 或扩展名无关：

```json
{
  "workspace_id": "feed-review-v1",
  "title": "Android 三方 Review Workspace",
  "default_ide": "idea",
  "versions": [
    {
      "id": "baseline",
      "label": "B · 扫描基线",
      "jump_label": "Baseline",
      "ref": "backup/ref"
    },
    {
      "id": "master",
      "label": "M · 当前 master",
      "jump_label": "Master",
      "ref": "origin/master"
    },
    {
      "id": "workspace",
      "label": "W · 修复后工作区",
      "jump_label": "Workspace",
      "ref": "HEAD + workspace"
    }
  ],
  "legend": {
    "focus": "用户参考行 / 修复聚焦行",
    "primary": "Baseline ↔ Master 差异",
    "secondary": "Master ↔ Workspace 差异"
  },
  "files": [
    {
      "id": "feed-ad-tools",
      "filename": "FeedAdTools.java",
      "path": "lib-ad-feed/.../FeedAdTools.java",
      "display_path": "FeedAdTools.java:88",
      "absolute_path": "/absolute/path/FeedAdTools.java",
      "ide_line": 88,
      "group": "lib_ad",
      "status": {
        "id": "diff-fix",
        "label": "差异化修复",
        "tone": "success"
      },
      "relation": "B = M ≠ W",
      "reference": "参考行：88",
      "conclusion": "工作区补齐 Lite 标记。",
      "action": "保留当前修复并补回归。",
      "versions": {
        "baseline": {
          "source_path": "snapshots/FeedAdTools.baseline.java",
          "language": "java",
          "marks": {
            "primary": [],
            "secondary": [88],
            "focus": [88]
          }
        },
        "master": {
          "source_path": "snapshots/FeedAdTools.master.java",
          "language": "java",
          "marks": {
            "primary": [],
            "secondary": [88],
            "focus": [88]
          }
        },
        "workspace": {
          "source_path": "snapshots/FeedAdTools.workspace.java",
          "language": "java",
          "marks": {
            "primary": [],
            "secondary": [88],
            "focus": [88]
          }
        }
      }
    }
  ]
}
```

二方模式不需要另一套模板，只保留两项 `versions` 即可。构建脚本会根据数量自动切换为两栏，例如：

```json
{
  "workspace_id": "before-after-review",
  "versions": [
    {
      "id": "before",
      "label": "Before · 修改前",
      "jump_label": "修改前"
    },
    {
      "id": "after",
      "label": "After · 修改后",
      "jump_label": "修改后"
    }
  ]
}
```

常见二方组合包括 `修改前 / 修改后`、`主版 / Lite`、`当前实现 / 目标实现`；需要区分基线演进和本地修复时，再使用三方模式。

### 顶层字段

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `workspace_id` | 是 | 小写稳定 ID；用于 DOM 和默认本地审阅状态 key |
| `title` | 否 | standalone 预览标题；正式报告章节标题仍由报告正文控制 |
| `storage_key` | 否 | 自定义 `localStorage` key；默认由 `workspace_id` 生成 |
| `default_ide` | 否 | 技术方案统一 IDE，只允许 `idea` / `xcode`；Android 方案设为 `idea`，iOS 方案设为 `xcode`，应用于 Workspace 内所有未显式覆盖的文件 |
| `versions` | 是 | 2 到 3 个版本，顺序就是窗格顺序 |
| `legend` | 否 | `focus` / `primary` / `secondary` 三类标记说明 |
| `files` | 是 | 非空文件数组 |

### 文件字段

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `id` | 是 | 文件稳定 ID，报告内唯一 |
| `filename` | 是 | 文件名 |
| `path` | 否 | 搜索和回退展示用路径 |
| `display_path` | 否 | 页面短标签；默认 `文件名:行号`，同名消歧最多增加一级父目录 |
| `absolute_path` | 否 | 必须是绝对路径；有值时按所选 IDE 构建 `idea://open` 或 `xcode://open` 链接，相对路径只放在 `path` |
| `ide` | 否 | 文件级 IDE 显式覆盖，只允许 `idea` / `xcode` |
| `ide_line` | 否 | IDE 跳转行；缺省时优先取右侧较新版本的首个 `focus` 行 |
| `idea_line` | 否 | 旧规格兼容字段，等价于 `ide_line`；新规格不要继续使用，两者同时存在时必须一致 |
| `group` / `repo` | 否 | 文件列表里的仓库、模块或分组 |
| `status` | 否 | 筛选状态；包含 `id`、`label`、`tone` |
| `relation` | 否 | 版本整体关系，例如 `B = M ≠ W` |
| `reference` | 否 | 参考行或矩阵信息 |
| `conclusion` | 否 | 当前文件结论 |
| `action` | 否 | 处理动作 |
| `versions` | 是 | 必须与顶层版本一一对应 |

`status.tone` 只使用：

- `neutral`
- `info`
- `success`
- `warning`
- `danger`

IDE 选择顺序：

1. 文件级 `ide` 显式覆盖。
2. 使用顶层 `default_ide`：Android 技术方案设为 `idea`，iOS 技术方案设为 `xcode`。
3. 不根据源码语言或扩展名推断 IDE；混合端方案通过文件级 `ide` 标明文件所属端。
4. 没有 `default_ide` 且文件未显式设置时，为兼容历史行为回退 IDEA。

Builder 新产物只写通用 `ideHref`。新版 runtime 和校验器仍可读取历史报告中的 `ideaHref`；
需要把新 Xcode Workspace 片段加入旧报告时，应同时重新生成首个带 runtime 的 Workspace，
避免旧 runtime 继续显示固定的 IDEA 按钮文案。

### 每个版本的源码字段

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `source_path` | 是 | UTF-8 源码快照路径 |
| `language` | 是 | 以 `highlight_code.py --list-langs` 为准 |
| `ref` | 否 | 覆盖顶层版本的 ref 文案 |
| `marks.primary` | 否 | 第一类差异行 |
| `marks.secondary` | 否 | 第二类差异行 |
| `marks.focus` | 否 | 参考行 / 修复聚焦行 |
| `marks.context` | 否 | “只看差异”保留行；缺省时脚本自动给标记行扩展上下 3 行 |

所有行号使用 1-based。越界行号会让构建脚本直接失败，避免打开页面后才发现跳转失效。

## 获取历史源码快照

源码快照由上游任务负责准备。常见方式：

```bash
git show origin/master:path/to/File.kt
git show backup/ref:path/to/File.kt
```

输出历史源码时使用明确的临时文件名，避免把不同版本覆盖到同一路径。构建完报告后，最终 HTML 已内嵌源码，不依赖这些临时文件继续存在。

如果是多仓或 MGIT 工程，先确认每个文件属于哪个仓库，再在对应仓库执行 `git show`；不要在错误仓库里把缺失文件误判成空版本。

## 安全与体积边界

- 必须由 `build_review_workspace.py` 生成数据节点。源码可能包含 `</script>`、`<`、`>`、`&`，脚本会做 HTML raw-text 安全转义；不要手工拼 JSON `<script>`。
- runtime 只把构建脚本生成的 `tok-*` 静态高亮写入 `innerHTML`；校验脚本会拒绝其他 HTML 标签。
- Workspace 仍是单文件离线组件，不加载 Monaco、CDN 或外部 JS。
- 推荐控制在 2 到 3 个版本、约 20 个文件以内。超过这个量时先缩小审阅范围，或把完整源码拆成多个报告；不要为了“功能完整”制造十几 MB 的难打开文件。
- 大文件只在用户确实需要全文关系判断时加入；普通 review 继续使用聚焦 diff。
- `localStorage` 只保存“已审阅文件 ID”，不承载评审结论或 Agent 交接数据。

## 响应式与打印

- 宽屏按版本并排，窗格不足时允许 Workspace 内部横向滚动。
- 900px 以下改为文件导航在上、版本窗格单列。
- 打印时隐藏工具栏、文件导航和复制按钮，按版本纵向输出静态源码。
- 重要结论必须在 Workspace 外的普通正文中出现，不能只藏在需要 JS 的交互区。
- IDE 跳转显示短标签，完整路径和行号保留在 `href` / `title`；工具栏按当前文件动态显示“IDEA 打开”或“Xcode 打开”，静态快照与 runtime 切换后的结构必须一致。

## 预览与回归

构建脚本提供 standalone 预览模式：

```bash
python3 skills/html-report/scripts/build_review_workspace.py workspace_spec.json \
  --standalone -o review_workspace_preview.html
python3 skills/html-report/scripts/check_html_report.py review_workspace_preview.html
```

`--standalone` 只用于组件视觉自审和回归，不替代正式报告的抬头、Findings、真实补丁、测试缺口和 Sources。
