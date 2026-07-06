# HTML 报告视觉规则

## 核心理念

HTML 相比 Markdown 的核心优势不是“能加 JS 交互”，而是可视化表达力：

- 卡片和网格：用卡片承载每个问题/结论，网格排列多方案对比。
- 颜色辅助信息：优先级标签、状态标记、文件 chip 色块配合文字，让读者快速感知严重程度。
- 图表与架构图：流程图、架构图、时间线按内容选择 SVG、表格或 ASCII。
- 表格天然适合对齐、比较和扫描。
- 排版余白、字号层级、折叠收纳用于提升阅读效率。

交互只是辅助，不要因为能做就加。一个只有折叠和复制按钮的干净报告，通常好过一个布满滑块和拖拽的页面。

## 设计原则

1. 可视优先，不是美观优先：最高优先级是让读者快速看懂结构、链路、差异和结论。
2. 整洁：视觉元素服务于信息分层，不堆颜色、不堆动画、不把报告做成海报。
3. 克制：加任何交互前先问自己，没有它读者会不会看不明白。如果不会，就不加。
4. 首屏即答案：打开页面不需要滚动、不需要点击就能看到核心结论。
5. 一页一事：每个卡片/区块只讲一件事。

## 核心视觉标准

- 页面背景柔和浅灰（`#f6f8fb`），主体内容居中，最大宽度 1180px。
- 总结区和问题区使用白色圆角卡片（14px），轻微阴影。
- 优先级、状态用彩色胶囊标签（P0 红 / P1 橙 / P2 蓝）。
- 文件路径和行号用 chip 样式（缩进色块 + 等宽字体）。
- 特别长的文件路径不要直接作为普通 `<code>` 完整展示；即使没有行号，也应按文件定位规则用 `...` 省略中间目录，保留仓库/模块线索、文件名和必要的方法/行号信息。
- 行内代码用灰色小反引号样式（`<code>` 标签，`#f1f5f9` 底 + `#334155` 字色）。
- 从 Markdown 内容生成 HTML 时，反引号包裹的短标识必须变成真实 `<code>` 标签，例如 `` `d` `` 输出为 `<code>d</code>`，不要把原始反引号文本留在正文里。
- 多行代码用接近 IDE 的深绿色背景块（`#10231f`），旁边放 copy 按钮，并对关键字、字符串、数字、注释等做颜色区分；默认采用 JetBrains 深色主题观感，关键字偏玫红、类型/常量偏黄绿、注释偏低饱和绿色。
- 使用 `tok-*` span 时必须同时带上 `.tok-key`、`.tok-str`、`.tok-num`、`.tok-cmt`、`.tok-fn`、`.tok-var`、`.tok-type` 等 CSS 定义；否则浏览器里会退化成纯文本。
- 长日志、次要章节用 `<details><summary>` 默认折叠。
- 长文档使用旧版左侧浮动目录固定导航，快速跳转到各章节；目录默认展开，并且必须能通过点击按钮收起/展开整个目录侧栏。
- 中文说明简洁准确，突出问题、影响和修复方案。

## SVG 技术图协作

当报告需要复杂技术图时，`html-report` 是编排方，`svg-tech-diagram` 是绘图方。不要要求用户同时显式调用两个 skill；由 `html-report` 判断是否需要图，并在需要时读取 `skills/svg-tech-diagram/SKILL.md` 及其相关 references。

适合使用 `svg-tech-diagram` 的场景：

- 技术方案里的架构图、模块关系图、数据流图。
- 问题排查/修复方案里的根因链路、修复路径、风险隔离关系。
- 代码导读报告里的执行链路、状态流转、调用分发关系。
- 多角色或多系统协作流程，表格/Mermaid/ASCII 难以在最终 HTML 中清楚表达。

不需要使用 SVG 技术图的场景：

- 2 到 4 项简单对比，用表格或网格卡片即可。
- 线性 3 到 5 步流程，用短列表或 Mermaid 已足够清楚。
- 只是装饰、封面或氛围图，不承担结构解释。

协作流程：

1. `html-report` 先确定报告章节和图要回答的问题。
2. 读取 `svg-tech-diagram`，让它按朴素技术图规范生成 SVG。
3. SVG 必须先渲染 PNG 并完成自审；有箭头穿文字、文字越界、信息拥挤时，先修图。
4. 自审通过后，优先把 `<svg>...</svg>` 内联进 HTML，外层使用 `.diagram-block`，SVG 使用 `.tech-diagram`。
5. 图下必须有 `<figcaption>`，说明图表达的结论或读图方式。
6. 最终仍由 `html-report` 运行 `check_html_report.py` 做单文件、响应式和代码块校验。

内联结构示例：

```html
<figure class="diagram-block">
  <svg class="tech-diagram" viewBox="0 0 1200 675" role="img" aria-labelledby="diagram-title diagram-desc">
    <title id="diagram-title">渲染链路架构图</title>
    <desc id="diagram-desc">展示输入、处理、校验和输出之间的关系。</desc>
    ...
  </svg>
  <figcaption>图 1：渲染链路从 SVG 生成、PNG 自审到 HTML 内联交付。</figcaption>
</figure>
```

注意：

- SVG 内部 class 建议加前缀，例如 `svgd-node`、`svgd-arrow`，避免和报告全局 `.tag`、`.grid` 等样式冲突。
- SVG 自身应包含 `<title>`、`<desc>`、`viewBox` 和内联样式，不能依赖页面外部 CSS 才能看懂。
- 如果不得不使用外部 `.svg` 文件，必须说明报告不再是完全单文件离线交付；默认不要这样做。

## 图片与视频证据支持

媒体证据是可选能力，不是所有 HTML 报告的必选内容。只有当截图、录屏、关键帧能明显提升证据表达时才加入；普通文字结论、表格或代码 diff 足够说明问题时，不要为了形式感添加媒体。

图片证据适合：

- UI 修复前后对比、移动端布局验收、异常状态截图。
- 数据看板、终端输出、浏览器页面或调试面板截图。
- 作为视频关键帧，让读者不用播放录屏也能先理解证据内容。

视频证据适合：

- 交互流程、动画、滚动、横竖屏切换、复现步骤。
- 单张截图无法表达时序或操作路径的场景。

生成规则：

- 默认把媒体资源放在 HTML 同目录的证据文件夹，例如 `evidence_20260625/xxx.png`、`evidence_20260625/xxx.mp4`，HTML 中使用相对路径引用。
- 小图可按需用 `data:image/...;base64,...` 内嵌；大图、长图和视频不要 base64，避免 HTML 膨胀和打开变慢。
- 图片使用 `<img>` 预览，并提供能说明证据内容的 `alt`。
- 视频使用 `<video controls preload="metadata">`，保留可播放预览；视频资源用 `<source src="evidence_20260625/xxx.mp4" type="video/mp4">` 或 `video src`。
- 视频证据建议同时放关键帧截图和原文件链接，例如 `<a class="media-link" href="evidence_20260625/xxx.mp4">打开原始录屏</a>`。
- 媒体卡片建议使用 `.media-evidence`，并通过标题、说明、对应 case、证据结论帮助读者快速扫读。它们是推荐结构，不是所有媒体块的硬性失败条件。
- 媒体仍要遵守响应式底线：图片和视频 `max-width: 100%; height: auto;`，外层可横向滚动，移动端不能把正文撑出视口。

推荐结构见 `references/css-template.md` 的“媒体证据结构”，样式来自 `references/css/media.css`。完成前运行 `check_html_report.py`；脚本会在媒体实际出现时检查本地相对路径、图片 `alt`、视频 `controls` 和响应式保护，并对缺少标题/说明/case/结论的媒体证据卡给出 warning。

## 响应式、打印与可访问性

HTML 报告是交付物，不只是桌面浏览器截图。生成时必须满足这些底线：

- 小屏幕、浏览器分屏和窄窗口下正文单列展示；左侧目录改成顶部普通导航，不遮挡正文，也不能让正文被挤出视口。
- 宽表格、代码块、ASCII 图必须 `overflow-x: auto`，不能撑破页面；卡片、网格和正文容器要有 `min-width: 0` 或等价约束，避免在分屏模式下显示不全。
- 卡片网格在窄屏降为单列；长路径 chip 允许换行或横向滚动，不能覆盖旁边文本。
- 打印样式去掉粘性定位、强阴影和无意义 hover 效果；链接文本、标题、表格和代码在黑白打印下仍可读。
- 状态和优先级不能只靠颜色表达，必须同时有文字，例如 `P1 高风险`、`已验证`、`待确认`。
- 图表、SVG、流程图附近必须有标题或一句解释；不要让读者只能靠图猜含义。
- 图片和视频如果作为证据出现，应有可读标题或说明；视频证据优先带关键帧截图，避免必须播放后才知道内容。
- 交互按钮要有可见文字或 `aria-label`，复制按钮点击后有状态反馈。
- 标题层级按 `h1 -> h2 -> h3` 递进，不为样式跳级。
- 正文、表格、代码和 diff 使用真实文本/HTML，不把重要内容做成图片。

## 文档抬头视觉规范

- 抬头位于正文最前面，比普通 `.summary` 更醒目，但仍然是工程文档风格。
- 推荐使用横向渐变或深色底的 `doc-header`，圆角不超过 16px，内部包含标题、简短说明和 meta chip。
- meta chip 可以包含文档类型、任务号、仓库、分支、负责人、日期、状态、平台端、版本等；不要塞太多，优先 4 到 8 个。
- 如果文档涉及多个仓库，用多个 chip 或一个“涉及仓库”列表；不要把长路径挤进标题。

## 文件定位链接规范

当报告里出现源码文件位置、`rg` 搜索结果、代码评审问题定位或堆栈归因时，文件路径应该既能被人读懂，也能一键跳转到 IDE。

- **结构先于样式**：源码定位必须先在 HTML 结构里表达正确，CSS 只负责视觉样式。不要指望 CSS 把拆散的路径和行号“拼成”一个定位；生成 HTML 时就必须产出单个可点击定位元素。
- 位置文本统一展示为单个 chip：`{displayPath}:{line}`、`{displayPath}:{start}-{end}` 或 `{displayPath}:{line}:{column}`；`line` 和 `column` 使用 1-based 数字。已有行号范围时必须展示完整范围，例如 `.../NadWrappedBrowserView.java:106-111`，不要写成 `...java:106` 后再另起一个 `106-111`。
- `displayPath` 优先使用仓库相对路径或从工作区根目录开始的短路径，便于阅读，例如 `browser-android/searchbox-lite/repos/business/ad_business/.../FlowVideoLandscapeHelper.kt:43-50`；如果无法可靠缩短，再展示绝对路径。
- 当路径过长导致 chip 挤占正文或换行难读时，展示文本可以用 `...` 省略中间目录，例如 `lib-ad-feed/.../UnitedSchemeADDispatcher.java:1350-1351`。省略只能发生在中间目录，不能省略仓库/模块线索、文件名、行号或行号范围；同名文件可能混淆时，保留更多父级目录。完整路径和完整定位放入 `title`，不要为了视觉省略破坏跳转信息。
- 对没有行号的长文件路径，也不要直接放完整 `<code>baiduapp-android/client/repos/business/lib_ad/lib-ad-feed/src/main/java/com/baidu/searchbox/feed/ad/scheme/UnitedSchemeAdDispatcher.java</code>`。优先生成单个 `.path` chip，例如 `<span class="path" title="baiduapp-android/client/repos/business/lib_ad/lib-ad-feed/src/main/java/com/baidu/searchbox/feed/ad/scheme/UnitedSchemeAdDispatcher.java">baiduapp-android/client/repos/business/lib_ad/lib-ad-feed/.../UnitedSchemeAdDispatcher.java</span>`；如果上下文指向方法，展示文本保留方法名，例如 `lib-ad-feed/.../UnitedSchemeAdDispatcher.java#makePhoneCall`。不要在路径中间硬换行。
- 有绝对路径时，文件位置必须渲染成 IDEA 协议链接：`idea://open?file={encodedAbsolutePath}&line={startLine}&column={column}`。行号范围用起始行作为跳转行，展示文本保留完整范围。HTML 属性里的 `&` 写成 `&amp;`，路径参数做 URL 编码，展示文本可按上一条规则缩短，但 `href` 和 `title` 必须保留完整可跳转定位。
- 必须使用同一个 `<a class="path file-link">` 同时承载路径和行号/行号范围。禁止把源码定位拆成 `<span class="path">...</span>` + `<span class="line">...</span>` 或“路径链接 + 单独行号 chip”；这种写法不能表达完整定位，也容易丢失跳转能力。

```html
<a class="path file-link" href="idea://open?file=/abs/path/File.java&amp;line=82&amp;column=7">/abs/path/File.java:82:7</a>
```

如果只有行号，链接和展示文本写成：

```html
<a class="path file-link" href="idea://open?file=/abs/path/File.java&amp;line=82">/abs/path/File.java:82</a>
```

如果是行号范围，链接跳到起始行，展示保留范围：

```html
<a class="path file-link" href="idea://open?file=/Users/markz/code/baidu/browser-android/searchbox-lite/repos/business/ad_business/flowvideo/src/main/java/com/baidu/searchbox/video/feedflow/ad/position/FlowVideoLandscapeHelper.kt&amp;line=43" title="/Users/markz/code/baidu/browser-android/searchbox-lite/repos/business/ad_business/flowvideo/src/main/java/com/baidu/searchbox/video/feedflow/ad/position/FlowVideoLandscapeHelper.kt:43-50">browser-android/searchbox-lite/.../FlowVideoLandscapeHelper.kt:43-50</a>
```

如果路径包含空格、`#`、`?`、`&` 或中文等非 ASCII 字符，`href` 里的 `file=` 参数必须做 URL 编码；展示文本保持人类可读，必要时按上方省略规则缩短。

如果只能拿到仓库相对路径且无法可靠还原绝对路径，可以先按 `{path}:{line}:{column}` 展示为 `.path` chip，但不要编造不可用的 `idea://open` 链接。

## 代码变更标识

当报告包含代码新增、删除、修改、修复方案或 patch 说明时，必须让读者不用对照上下文也能看出哪里变了。不要只展示一段“修复后代码”，也不要把旧代码混在方案里却不标注。

优先级：

1. **聚焦 diff**：适合行级修改、review 问题、补丁说明。有真实 unified diff 时必须用 `scripts/highlight_code.py --lang diff --diff-view` 生成 `.diff-card.diff-viewer`，保持 old/new 行号、红绿整行背景、左侧变更轨道、hunk header 和代码列语法高亮的固定样式。生成后的 `<section class="diff-card diff-viewer">...</section>` 片段要原样嵌入报告，不能重新包一层普通代码块，不能把行号列拆到外层，也不要手写 `.diff-card` 或把 diff 做成普通 `language-diff` / `language-text` 代码块。old/new 行号列应按内容自适应，保留 40px 最小宽度；`+/-` 轨道保持 25px，避免左侧指示器在窄屏下挤占代码区。
2. **Before / After 双栏**：适合结构变化较大、需要对比旧方案和新方案。左栏标题写“修改前”，右栏标题写“修改后”，两栏都必须只保留必要片段。
3. **新增代码块**：适合纯新增文件、纯新增方法或纯新增配置。标题和 badge 必须写“新增”，左侧使用绿色竖线，不要让它看起来像普通代码摘录。
4. **删除代码块**：适合删除旧逻辑。标题和 badge 必须写“删除”，左侧使用红色竖线，并说明删除原因或替代逻辑。

每个变更块应包含：

- 文件 chip：`{path}:{line}` 或 `{path}:{line}:{column}`。
- 状态 badge：`新增` / `删除` / `修改` / `建议变更` / `上下文`。
- 变更摘要：一句话说明为什么改。
- 代码区域：带行号或 `+/-/~` 标记；上下文行保留 3 到 5 行即可。

行级规则：

- 新增行：绿色背景、左侧 `+`、可用 `<ins>` 或 `.diff-mark-add` 标记新增 token。
- 删除行：红色背景、左侧 `-`、可用 `<del>` 或 `.diff-mark-del` 标记删除 token。
- 修改行：优先拆成相邻的删除行和新增行；如果只是行内小改，可用 `~` 行配合 `<del>` / `<ins>` 做 token 级标记。
- 上下文行：中性背景、左侧空白或 `·`，避免用强颜色。
- 如果没有真实旧代码，只能展示新增方案，明确标成“建议新增”，不要写成“修改”。

真实 unified diff 示例结构应与 `highlight_code.py --lang diff --diff-view` 输出保持一致：

```html
<section class="diff-card diff-viewer">
  <div class="diff-header">
    <span class="change-chip change-mod">代码差异</span>
    <span class="muted">统一 diff · old/new 行号</span>
  </div>
  <div class="diff-scroll">
    <table class="diff-table" aria-label="代码差异">
      <tbody>
        <tr class="diff-line diff-hunk"><td class="diff-gutter"></td><td class="diff-num diff-old-num"></td><td class="diff-num diff-new-num"></td><td class="diff-code">@@ -5,1 +5,1 @@</td></tr>
        <tr class="diff-line diff-del"><td class="diff-gutter">-</td><td class="diff-num diff-old-num">5</td><td class="diff-num diff-new-num"></td><td class="diff-code">description: 旧描述</td></tr>
        <tr class="diff-line diff-add"><td class="diff-gutter">+</td><td class="diff-num diff-old-num"></td><td class="diff-num diff-new-num">5</td><td class="diff-code">description: 新描述</td></tr>
      </tbody>
    </table>
  </div>
</section>
```

如果报告里同时有很多改动，先用一个“变更总览”表列出文件、类型、影响，再把长 diff 放进 `<details>`。

## 长文档目录导航

满足任一条件就视为长文档：

- 一级/二级章节超过 5 个。
- 内容包含多组问题、方案、链路、日志或验证结果。
- 预期阅读需要多次上下滚动定位。

生成长文档时：

- 使用固定在左侧的 `<aside class="toc">` 展示目录，正文放入 `<main class="content">`。
- 目录必须沿用旧版浮动 `<aside class="toc">` 卡片结构，包含 `.toc-title`、直接锚点链接和 `.toc-toggle` 按钮；默认展开，读者点击按钮时切换 `.toc-collapsed`，收起/展开整个目录侧栏。不要使用 `<details class="toc-details">` 只折叠目录内部链接。
- 目录项对应正文主要 `<h2>` 章节，每个章节设置稳定的 `id`，目录用锚点跳转。
- 当前不需要复杂 JS 高亮；保持目录常驻、简洁、可点击即可。
- 小屏幕下目录改为顶部普通卡片，不遮挡正文。
- 短报告不要强行加目录，避免页面显得笨重。

## ASCII 架构图与代码块

代码块不能只是深色背景加纯文本，也不要靠模型手工包大量 `tok-*` span。报告中的多行代码、SQL、XML、JSON、配置片段和 diff 必须使用 `scripts/highlight_code.py` 生成安全 HTML 片段：普通代码输出 `.code-wrap`，真实 unified diff 输出 `.diff-card.diff-viewer`。最终 HTML 必须是静态离线输出，不在浏览器运行 highlight.js、Prism、Shiki，也不从 CDN 拉取资源：

```bash
python3 skills/html-report/scripts/highlight_code.py --lang kotlin snippet.kt
python3 skills/html-report/scripts/highlight_code.py --lang objc view_controller.m
python3 skills/html-report/scripts/highlight_code.py --lang swift view_model.swift
python3 skills/html-report/scripts/highlight_code.py --lang sql query.sql
python3 skills/html-report/scripts/highlight_code.py --lang json payload.json
python3 skills/html-report/scripts/highlight_code.py --engine auto --lang kotlin snippet.kt
python3 skills/html-report/scripts/highlight_code.py --lang diff --diff-view patch.diff
python3 skills/html-report/scripts/highlight_code.py --list-langs
```

脚本会先转义 HTML，再做静态高亮，并输出可直接嵌入报告的 HTML 片段。普通代码输出 `<div class="code-wrap">...</div>`；真实 unified diff 必须使用 `--diff-view` 输出 `.diff-card.diff-viewer`，不要使用普通 `language-diff` 代码块。支持语言和常见别名以 `--list-langs` 的 JSON 输出为准，这是语言注册表的单一真源；不要在 reference 里手写第二份完整清单。默认 `--engine builtin` 零依赖输出 `tok-*` class；diff viewer 会根据 `---` / `+++` 文件路径后缀推断语言，并复用同一套 builtin 高亮给代码列生成 `tok-*` token。`--engine auto` 会在本机可用 Pygments 模块或 `pygmentize` CLI 时改用 Pygments inline style 预渲染，否则自动回退 builtin；`--engine pygments` 则要求 Pygments 可用。不要在生成报告时静默安装 Pygments；只有用户明确要求安装/增强高亮时，才征得确认后安装。Shiki、highlight.js、Prism 如需使用，也必须只在生成阶段本地预渲染，不能把外部 JS/CSS 依赖带进最终报告。当输入是真实 unified diff 且需要展示修改点时，必须使用 `--diff-view` 输出类似代码评审工具的 `.diff-card.diff-viewer`，包含 old/new 行号、红绿整行背景、左侧变更轨道、hunk header 和代码列语法高亮。

脚本不可用时，不要直接交付未高亮代码块；先修正脚本路径、临时文件或语言参数并重试。确实无法运行脚本时，才手工使用以下规则：

- 优先用 `<span class="tok-key">`、`tok-str`、`tok-num`、`tok-cmt`、`tok-fn`、`tok-var` 等 class 标出关键字、字符串、数字、注释、函数名和变量名。
- 不需要完整编译级语法分析，但至少要让读者一眼区分注释、字符串、关键逻辑和普通标识符。
- 差异代码不要手工改成普通代码块；只有在脚本路径、临时文件和语言参数都修复后仍无法运行时，才按 `.diff-card.diff-viewer` 的结构手工补齐固定样式。手工补齐时必须包含 `.diff-header`、`.diff-scroll`、`.diff-table`、`.diff-gutter`、`.diff-old-num`、`.diff-new-num`、`.diff-code`、`.diff-hunk` 和 `.diff-add` / `.diff-del`，并内联 `references/css/code-diff.css` 中完整 diff viewer CSS。
- 短代码块只高亮确定的核心 token；如果不确定，保持转义后的纯文本更好。
- 代码内容必须先转义 HTML，再包高亮 span，避免 `<`、`>`、`&` 破坏页面。
- 多行代码块必须放在 `.code-wrap` 容器中，使用 `<pre><code class="language-xxx">...</code></pre>`，右上角提供复制按钮。
- 完成前运行 `scripts/check_html_report.py`。支持高亮的语言应包含至少一种 `tok-*` token 或 Pygments inline style；使用 `tok-*` 时还必须有对应 CSS 定义；`text`、日志和纯文本只要求已转义并包在 `.code-wrap` 中。

ASCII/树状架构图必须保持原始换行、缩进和连接符，不要让浏览器自动换行破坏结构。ASCII 图使用专用浅色容器，例如 `<pre class="ascii-diagram">...</pre>`，并内联 `references/css/code-diff.css`，确保包含等宽字体、`white-space: pre`、`overflow-x: auto`、合适行高和横向滚动。

## 可用交互

几乎所有报告都该有：

- 折叠：`<details><summary>`，零 JS，原生支持。折叠堆栈日志、大段 diff、次要分析。
- 复制按钮：代码块右上角一个低调的小按钮，hover 才显示。点击复制后反馈“已复制”1.5 秒。

视情况使用：

- 左侧目录：当报告较长、章节超过 5 个或需要频繁跨章节查阅时使用；默认展开，可点击按钮整体收起/展开侧栏。
- 标签页：当报告天然有 2 到 3 个并列视角时用，如“问题/修复/验证”“方案 A/B/C”。用纯 CSS 实现，不引入 JS。
- 可排序表格：5 行以上数据表才加表头点击排序。3 到 4 行的迷你表不需要。
- 离线批注审核模式：当用户需要在 HTML 内选中文本提问/批注，或需要导出给 Agent 的 Markdown/JSON 提问包时使用；先生成普通 HTML，再运行 `scripts/inject_annotation_mode.py` 注入，不要手写批注 JS。

以下能力仅当用户明确要求对应场景时才加入：

- 滑块/开关调参（仅设计原型场景）
- 拖拽排序（仅 ticket 排序场景）
- 实时预览编辑器（仅 prompt 调试场景）
- 表单编辑器（仅配置管理场景）

## 使用场景速查

| 场景 | 关键可视化手段 | 可选交互 |
| --- | --- | --- |
| 代码评审报告 | 优先级标签、文件 chip、代码 diff 深色块 | 折叠长 diff、复制按钮 |
| 问题排查/修复方案 | 问题卡片、根因流程图、修复 check-list | 折叠堆栈、标签页 |
| 技术方案/设计文档 | SVG 架构图、方案对比网格、关键代码片段 | 左侧目录、折叠备选方案、标签页 |
| 概念讲解/学习笔记 | SVG 示意图、表格总结、分级标题 | 左侧目录、折叠深入阅读 |
| 多方案对比 | 网格卡片并列、每卡标题+要点+取舍说明 | 折叠每卡详情 |
| 正式技术/业务文档 | 文档抬头、meta chip、摘要卡片、目录导航 | 左侧目录、折叠附录/证据 |
| 需要内部审阅的报告 | 正常报告结构 + 离线批注审核模式 | 选区提问/批注、右侧栏、Markdown/JSON 提问包、导出发布版 |
