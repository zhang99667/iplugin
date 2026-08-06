# HTML Report 组件契约

本文件是组件结构、依赖和渐进增强行为的操作规范。组件资产的机器可读真源是
`assets/components/registry.json`，统一装配入口是 `scripts/assemble_report.py`。

## 1. 分层

| 层级 | 组件 | 职责 |
| --- | --- | --- |
| Core | `base`、`interactions` | 页面基础、打印和原生折叠反馈；默认装配 |
| Content | `table`、`code-block`、`media`、`diagram` | 承载一种稳定内容结构 |
| Navigation | `file-location`、`toc` | 文件和章节定位 |
| Behavior | `image-lightbox`、`tabs`、`sortable-table` | 在语义内容上增加可选交互 |
| Pattern | `diff-viewer`、`review-workspace` | 组合多个基础组件完成复杂审阅任务 |

这些组件不是独立 skill。它们没有独立用户意图和触发边界，只是 `html-report` 的内部积木。
批注模式也是复合模块，但属于生成后的注入流程，不进入普通页面组件注册表。

## 2. 注册组件

| 组件 | 自动检测标记 | 依赖 | 无 JS 回退 |
| --- | --- | --- | --- |
| `base` | 默认 | 无 | 完整正文 |
| `interactions` | 默认 | `base` | `<details>` 原生可用；只失去回到顶部增强 |
| `table` | `.table-wrap` | `base` | 普通表格可读、可横向滚动 |
| `file-location` | `.file-location` / `.file-link` | `base` | `idea://` 链接仍可点击 |
| `code-block` | `.code-wrap` / `.ascii-diagram` | `base`、`interactions` | 代码仍可选中；只失去复制按钮增强 |
| `diff-viewer` | `.diff-viewer` | `code-block` | 完整 diff 表格可读 |
| `media` | `.media-evidence` / `.media-frame` | `base` | 图片和视频仍可直接查看 |
| `image-lightbox` | `.image-lightbox-trigger[data-image-lightbox]` | `base` | 原图链接直接打开 |
| `diagram` | `.diagram-block` / `.tech-diagram` | `base` | SVG 和 caption 可读 |
| `toc` | `.layout-with-toc` / `.toc-toggle` | `base` | 目录默认展开且锚点可用 |
| `tabs` | `.report-tabs[data-tabs]` | `base` | 所有面板按顺序展示 |
| `sortable-table` | `table.sortable` | `table` | 保留原始表格顺序 |
| `review-workspace` | `.review-workspace` | `base`、`interactions`、`file-location`、`code-block` | 首文件静态快照可读 |

`interactions` 是所有新报告都会装配的默认组件。runtime 在滚动超过 360px 后创建并显示右下角
`.back-to-top` 按钮，点击返回页面顶部；按钮在短页面中不进入 Tab 顺序，尊重
`prefers-reduced-motion`，打印时隐藏。导出的批注版可能保留动态按钮，因此 runtime 使用
`window` 级防重复标记并复用已有节点，确保重新打开后重新绑定事件。

## 3. 普通表格

普通表格必须使用统一 wrapper。`table` 组件由 `.table-wrap` 负责小圆角外框裁切和窄屏滚动，
单元格继续显示完整 1px 网格线；排序行为不再维护第二套表格外观。

```html
<div class="table-wrap">
  <table>
    <thead><tr><th>项目</th><th>结论</th></tr></thead>
    <tbody><tr><td>网格线</td><td>通过</td></tr></tbody>
  </table>
</div>
```

`.table-wrap` 是唯一外层视觉边界，不额外添加 wrapper 边框，避免与单元格外沿形成双线。
`.diff-table` 属于 `diff-viewer`，不套普通表格规则。

## 4. IDE 文件定位

可见标签固定为 `文件名:起始行-结束行`；只有同页出现同名文件、确实需要消歧时，才增加
一级父目录。完整路径只保留在 `href` 和 `title`，避免仓库路径撑破正文。

```html
<a class="file-location file-link"
   href="idea://open?file=/repo/business/flowvideo/FlowVideoHelper.kt&amp;line=1050"
   title="/repo/business/flowvideo/FlowVideoHelper.kt:1050-1070">FlowVideoHelper.kt:1050-1070</a>
```

同名文件消歧示例：

```text
flowvideo/FlowVideoHelper.kt:1050-1070
```

约束：

- 行范围跳转到起始行，展示和 `title` 保留完整范围。
- `href` 的文件路径、起始行必须与 `title` 一致。
- 短标签的文件名、父目录和行范围必须与完整定位一致。
- 没有绝对路径时使用不可点击的 `.path` 文本，不编造 `idea://` 链接。

## 5. 代码和 Diff

代码、日志、配置和 ASCII 片段使用 `scripts/highlight_code.py` 生成 `.code-wrap`；真实 unified
diff 使用 `--diff-view` 生成每文件独立的 `.diff-card.diff-viewer`。不要手写高亮 token、复制
runtime 或 diff 表格。普通代码块的 `.code-toolbar` 使用 `span` 作为稳定工具栏，复制按钮在
悬停代码块或键盘聚焦时显示，`.code-lang` 语言标签始终贴在工具栏最右侧；触摸设备不依赖
hover，继续保留可操作的复制按钮。

```bash
python3 skills/html-report/scripts/highlight_code.py --lang kotlin snippet.kt
python3 skills/html-report/scripts/highlight_code.py --lang diff --diff-view patch.diff
```

生成的普通代码块结构如下，语言名使用规范化后的可读标签，不直接暴露原始别名：

```html
<div class="code-wrap" data-code-lang="python">
  <span class="code-toolbar" role="group" aria-label="代码工具栏">
    <button class="copy-btn" type="button">复制</button>
    <span class="code-lang" data-code-lang="python">Python</span>
  </span>
  <pre><code class="language-python">...</code></pre>
</div>
```

`diff-viewer` 依赖 `code-block`，装配器会自动加入静态 token 样式。复制按钮只是增强；没有
JS 时源码仍保持可读和可选中，旧版 `.code-wrap` 也会由 runtime 补齐工具栏和语言标签。
需要关闭复制时使用 `highlight_code.py --no-copy`，生成器会保留语言标签并在根节点写入
`data-copy="false"`，校验器据此区分有意关闭和意外缺失。

## 6. 图片与灯箱

媒体证据图片必须以原图链接作为无 JS 回退，再用页面级单例 `<dialog>` 增强点击放大。

```html
<figure class="media-evidence" data-case="case-01" data-conclusion="布局无溢出">
  <div class="media-frame">
    <a class="image-lightbox-trigger"
       data-image-lightbox
       href="evidence_20260729/case_01.png"
       data-lightbox-caption="case-01 修复后截图">
      <img src="evidence_20260729/case_01.png" alt="case-01 修复后布局截图">
    </a>
  </div>
  <figcaption class="media-caption">case-01 修复后截图</figcaption>
</figure>
```

视频不进入图片灯箱，继续使用 `<video controls preload="metadata">`。图片 `alt`、原图 `href`
和响应式尺寸都是硬契约。

## 7. 目录

长文档使用默认展开的左侧目录。runtime 只负责整体收起，不负责生成目录内容。

```html
<div class="layout-with-toc">
  <aside class="toc" aria-label="目录">
    <div class="toc-header">
      <p class="toc-title">目录</p>
      <button class="toc-toggle" type="button" aria-label="收起目录"
              aria-expanded="true" title="收起目录">
        <span class="toc-toggle-icon" aria-hidden="true">‹</span>
      </button>
    </div>
    <a href="#summary">最终结论</a>
  </aside>
  <main><section id="summary">...</section></main>
</div>
```

不要用 `<details>` 包目录。禁用 JS 时目录仍默认展开，锚点仍可跳转。

## 8. Tabs

只有 2 到 3 个并列视角才使用 Tabs。根节点、按钮和面板必须保留完整 ARIA 关联；runtime
启动前所有面板都显示，避免脚本失败后内容消失。

```html
<section class="report-tabs" data-tabs>
  <div class="tabs" role="tablist" aria-label="报告视图">
    <button id="tab-findings" class="tab-label" type="button" role="tab"
            aria-selected="true" aria-controls="panel-findings">问题</button>
    <button id="tab-fixes" class="tab-label" type="button" role="tab"
            aria-selected="false" aria-controls="panel-fixes">修复</button>
  </div>
  <div class="tab-content">
    <section id="panel-findings" class="tab-panel" role="tabpanel"
             aria-labelledby="tab-findings">...</section>
    <section id="panel-fixes" class="tab-panel" role="tabpanel"
             aria-labelledby="tab-fixes">...</section>
  </div>
</section>
```

键盘支持左右方向键、Home 和 End。一个视角不要套 Tabs。

## 9. 可排序表格

只有 5 行以上、读者确实需要比较的数据表才启用。表头使用真实按钮，状态箭头保留独立槽位。

```html
<div class="table-wrap">
  <table class="sortable">
    <thead><tr><th><button class="sort-button" type="button" data-sort-type="number">
      数量<span class="sort-arrow" aria-hidden="true"></span>
    </button></th></tr></thead>
    <tbody>...</tbody>
  </table>
</div>
```

支持 `auto`、`number` 和 `date`。排序保持相等项的原始顺序；无 JS 时表格按生成顺序展示。

## 10. 维护门禁

新增或调整组件时同时完成：

1. 在 `assets/components/<name>/` 放置真实 CSS/JS 资产。
2. 更新 `assets/components/registry.json` 的类别、依赖、资产和稳定检测标记。
3. 让 runtime 使用 `HTML_REPORT_<NAME>_RUNTIME_START/END` 完整性标记，并保护重复初始化。
4. 在 `scripts/tests/test_report_components.py` 增加正向、缺依赖或坏结构的反向用例。
5. 必要时扩展 `check_html_report.py` 的确定性结构门禁，不评价内容审美。
6. 运行 `scripts/build_component_gallery.py` 更新标准 Gallery，确认默认、长内容、空状态和交互态仍能组合展示。
7. 运行装配幂等测试、组件测试、真实报告校验和插件全仓校验。

不要把组件拆成新 skill，也不要把 CSS/JS 源码复制回 reference。
