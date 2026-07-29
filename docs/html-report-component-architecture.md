# HTML Report 组件化架构设计

- 状态：Implemented
- 日期：2026-07-29
- 对应插件版本：`0.22.14`
- 对应 skill 版本：`html-report 0.6.0`

## 1. 背景

`html-report` 原先已经把部分 CSS 拆到多个文件，但生成过程仍要求 Agent 临场选择、复制和
拼接 CSS/JS。表格边框、Diff、目录和复制按钮等能力容易因漏贴资产、结构漂移或脚本重复而
不稳定。随着 Review Workspace、评论模式、媒体证据等能力增加，继续扩展单个模板会同时
放大上下文成本和回归面。

本次改造把一个对外 skill 保留下来，在内部建立可组合组件、统一装配器和组件级门禁。目标
是让 Agent 负责内容和语义结构，让确定性脚本负责依赖解析、资产内联和一致性校验。

## 2. 决策

采用“一个 skill，多层内部组件”的结构，不为 Table、Diff、Lightbox 等 UI 单元创建独立
skill。

原因：

- `html-report` 是用户可感知的完整任务；Table、Diff 和目录没有独立触发语义。
- 独立 skill 会增加选择冲突、上下文加载和跨 skill 版本协同成本。
- UI 组件需要确定性装配和测试，更适合作为 `assets + scripts`，而不是继续增加自然语言指令。
- 组件仍能像积木组合，但组合边界由注册表和依赖图约束。

## 3. 外部案例与边界

没有发现一个被广泛采用、与本仓库完全一致的“HTML report skill 组件注册表”标准。本设计
采用的是两个成熟方向的交集：

1. [Agent Skills Specification](https://agentskills.io/specification) 明确支持一个 skill 内按
   `scripts/`、`references/`、`assets/` 分层，并建议通过 progressive disclosure 将详细材料
   按需加载。这支持“保持一个 skill，把确定性实现放入资产和脚本”的方向。
2. [Storybook: Why Storybook?](https://storybook.js.org/docs/get-started/why-storybook) 描述了
   component-driven 工作流：组件隔离开发、覆盖不同状态、再逐步组合成复杂页面。这支持
   组件级契约和独立回归，而不是只测完整报告。
3. [MDN: Progressive enhancement](https://developer.mozilla.org/en-US/docs/Glossary/Progressive_Enhancement)
   强调先保证基础内容和功能可用，再增加浏览器能力。本设计据此要求 Tabs、TOC、排序和
   Lightbox 在 JS 不可用时仍保留可读内容或原生链接。
4. [GitHub 文件永久链接文档](https://docs.github.com/en/repositories/working-with-files/using-files/getting-permanent-links-to-files)
   明确支持链接到单行或行范围；[IntelliJ IDEA 命令行打开文件文档](https://www.jetbrains.com/help/idea/opening-files-from-command-line.html)
   说明文件路径和起始行是定位核心。两者共同支持“短标签展示，完整目标隐藏在链接中”的
   IDE 定位组件设计。

这些资料证明分层、组件隔离、渐进增强和行定位的合理性，但不意味着外部存在与本实现完全
相同的注册表格式。

## 4. 总体分层

```text
用户任务
  |
  v
html-report SKILL.md              用户意图、内容编排、执行顺序
  |
  +--> references/                按需读取的结构和视觉契约
  |
  +--> 语义 HTML / 生成器片段     Agent、highlight_code、Workspace builder
  |
  v
assemble_report.py                检测组件 -> 解析依赖 -> 内联 CSS/JS
  |
  v
单文件 HTML
  |
  +--> check_html_report.py       结构、依赖、runtime、无障碍和响应式门禁
  |
  +--> inject_annotation_mode.py  可选后处理：评论模式
```

职责边界：

| 层 | 负责 | 不负责 |
| --- | --- | --- |
| Skill | 是否生成 HTML、叙事主线、内容完整性、组件选择 | 手贴 CSS/JS、解析依赖 |
| Reference | 组件何时用、语义结构、视觉原则 | 保存真实 runtime 源码 |
| Asset | 可内联 CSS/JS 和复合模块资产 | 用户触发和内容编排 |
| Assembler | 检测、依赖展开、去重、稳定顺序、幂等内联 | 生成业务正文 |
| Validator | 确定性结构与资产契约 | 主观审美和内容结论 |

## 5. 目录结构

```text
skills/html-report/
├── SKILL.md
├── assets/
│   ├── components/
│   │   ├── registry.json
│   │   ├── base/style.css
│   │   ├── table/style.css
│   │   ├── file-location/style.css
│   │   ├── code-block/{style.css,runtime.js}
│   │   ├── diff-viewer/style.css
│   │   ├── media/style.css
│   │   ├── image-lightbox/{style.css,runtime.js}
│   │   ├── diagram/style.css
│   │   ├── toc/{style.css,runtime.js}
│   │   ├── tabs/{style.css,runtime.js}
│   │   └── sortable-table/{style.css,runtime.js}
│   ├── review-workspace/{workspace.css,workspace.js}
│   └── annotation-mode/
├── references/
│   ├── css-template.md
│   ├── component-contracts.md
│   └── ...
└── scripts/
    ├── assemble_report.py
    ├── highlight_code.py
    ├── build_review_workspace.py
    ├── inject_annotation_mode.py
    └── check_html_report.py
```

CSS/JS 是输出资产，所以放入 `assets/`；组件说明是 Agent 按需读取的知识，所以放入
`references/`。架构决策属于仓库维护记录，因此单独放在根目录 `docs/`。

## 6. 组件模型

组件分四层：

| 层级 | 组件 | 说明 |
| --- | --- | --- |
| Core | `base`、`interactions` | 所有报告默认能力 |
| Content | `table`、`code-block`、`media`、`diagram` | 单一内容类型 |
| Navigation | `file-location`、`toc` | 文件和章节定位 |
| Behavior | `image-lightbox`、`tabs`、`sortable-table` | 可选交互增强 |
| Pattern | `diff-viewer`、`review-workspace` | 组合多个基础组件的复合模式 |

注册表为每个组件记录：类别、说明、依赖、CSS、JS、自动检测 class/attribute。装配器递归展开
依赖并去重，最终按稳定顺序输出。页面同时写入：

- `data-html-report-components`：本次报告装配的组件列表。
- `data-html-report-runtime`：每个内联 runtime 的归属。

这两个属性是构建产物和校验输入，不是作者手写 API。

## 7. 关键组件决策

### 7.1 Table

普通表格从 `base` 中拆出独立 `table` 组件。任何非 Diff 表格都使用
`.table-wrap > table`，统一完整 1px 网格线和横向滚动。`sortable-table` 只增加行为并依赖
`table`，不维护第二套表格外观。

### 7.2 Code 与 Diff

`code-block` 负责代码容器、静态 token 和复制行为；`diff-viewer` 依赖它，只增加 unified
diff 的文件标题、old/new 行号和增删状态。源码片段继续由 `highlight_code.py` 确定性生成。

### 7.3 IDE 文件定位

默认展示：

```text
FlowVideoHelper.kt:1050-1070
```

只有同页同名时最多增加一级父目录：

```text
flowvideo/FlowVideoHelper.kt:1050-1070
```

完整绝对路径和行范围保存在 `title`，`idea://` 的 `href` 保留完整路径并跳到起始行。这样既
保留一键跳转和悬停信息，也避免长仓库路径挤占报告布局。校验器会比对短标签、`title` 和
`href`，避免三者指向不同文件或行号。

### 7.4 Image Lightbox

媒体证据图片必须先是原图 `<a href>`，再通过 `data-image-lightbox` 增强。支持原生
`<dialog>` 的浏览器使用页面级单例灯箱；不支持或禁用 JS 时直接打开原图链接。视频保持原生
controls，不复用图片灯箱。

### 7.5 TOC、Tabs 与排序

- TOC 默认展开，runtime 只控制整体收起；禁用 JS 时锚点仍可用。
- Tabs 在 runtime 启动前依次显示所有面板，启动后才隐藏未激活面板。
- 排序只改变表格行顺序，禁用 JS 时保留原始顺序。

三者均使用重复初始化保护，避免报告被二次装配或复合模块重复挂载。

### 7.6 Review Workspace 与评论模式

Review Workspace 是注册表中的 Pattern，但正文、数据和唯一 workspace runtime 仍由
`build_review_workspace.py` 生成；装配器负责补齐样式和基础依赖。

评论模式不进入普通组件注册表。它会修改既有 HTML、增加批注交接包，并且有发布版剥离
语义，适合作为基础报告校验通过后的独立后处理阶段。

## 8. 装配流程

```text
输入语义 HTML
  -> 删除旧的受管样式/runtime 块
  -> 加入 defaults
  -> 按稳定 class/attribute 自动检测
  -> 合并显式组件
  -> 拓扑展开依赖并检查循环
  -> 校验资产未越出 skill 且不含结束标签
  -> 去重并内联 CSS/JS
  -> 写入组件声明
```

重复运行必须逐字输出相同结果。装配器只管理带
`HTML_REPORT_COMPONENT_*_START/END` 的块，不删除报告作者自己的正文或其他脚本。

## 9. 校验与测试

组件级测试覆盖：

- 注册表所有组件和资产都能解析。
- 自动检测、依赖展开、稳定顺序和重复装配幂等。
- 普通表格完整网格线与错误 wrapper 反例。
- 每文件独立 Diff 与多文件混装反例。
- 图片灯箱正反例。
- IDE 短标签、完整目标及路径不一致反例。
- Tabs ARIA 结构、TOC runtime、排序按钮和 runtime 完整性。
- Review Workspace standalone 预览与真实校验器组合。

仓库级 `scripts/validate-plugin.py` 额外检查注册表 schema、依赖、资产路径、结束标签和 runtime
完整性标记，防止组件只改一半。

## 10. 迁移策略

1. 将旧 `references/css/*.css` 迁入 `assets/components/*/style.css`。
2. 把原 `code-diff.css` 拆成 `code-block` 和 `diff-viewer`。
3. 把普通表格从 `base` 拆成 `table`。
4. 将复制、TOC、Tabs 和排序脚本从文档示例迁入各自 runtime。
5. 新增 `file-location` 和 `image-lightbox`。
6. Review Workspace standalone 预览改走统一装配器。
7. 新生成报告强制使用装配器；校验器暂时兼容没有组件声明的历史报告。

历史 HTML 不做批量重写。需要重新生成或继续维护时，再迁移到新流程。

## 11. 版本策略

这是 `html-report` 内部生成架构的较大重构，skill 从 `0.5.3` 升级到 `0.6.0`。

没有新增 skill，插件版本继续遵守 `0.<累计新增 skill 数>.<优化次数>`，从 `0.22.13` 升级到
`0.22.14`。不使用标准 SemVer Major 改写插件第一位，也不改变第二位累计 skill 数。

## 12. 排除项

- 不把每个组件发布为独立 skill。
- 不引入 React、Vue、Web Components framework 或运行时依赖。
- 不引入 CDN、Monaco、前端构建链或 npm 依赖。
- 不在浏览器运行语法高亮；继续生成期静态高亮。
- 不自动迁移历史 HTML。
- 不让组件系统决定报告章节；内容叙事仍由 skill 根据读者任务设计。

## 13. 后续扩展门槛

新增组件前必须同时满足：

1. 至少两个报告场景可复用。
2. 有稳定语义 class/attribute，不依赖正文关键词猜测。
3. 能定义无 JS 回退或明确说明为何不适用。
4. 依赖关系可进入注册表，不需要业务专用条件分支。
5. 有正向和故障注入测试。

不满足这些条件的局部样式继续留在具体报告语义中，不进入公共组件层。
