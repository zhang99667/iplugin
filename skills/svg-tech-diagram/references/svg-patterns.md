# SVG 技术图模式库

## 画布骨架

新图优先从这个浅色、朴素的骨架开始，按需要调整 `viewBox` 和标题。

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 675" role="img" aria-labelledby="title desc">
  <title id="title">技术图标题</title>
  <desc id="desc">一句话说明图表达的结构。</desc>
  <defs>
    <marker id="arrowNeutral" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#475569"/>
    </marker>
    <marker id="arrowPrimary" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2563EB"/>
    </marker>
    <style>
      .text-main { fill: #0F172A; font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Noto Sans CJK SC", "Segoe UI", sans-serif; }
      .text-body { fill: #334155; font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Noto Sans CJK SC", "Segoe UI", sans-serif; }
      .text-muted { fill: #64748B; font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Noto Sans CJK SC", "Segoe UI", sans-serif; }
      .node { fill: #FFFFFF; stroke: #CBD5E1; stroke-width: 1.2; }
      .group { fill: #F8FAFC; stroke: #CBD5E1; stroke-width: 1.2; stroke-dasharray: 6 5; }
      .arrow { fill: none; stroke-width: 2.2; stroke-linecap: round; stroke-linejoin: round; }
    </style>
  </defs>
  <rect width="1200" height="675" fill="#FFFFFF"/>
</svg>
```

## 节点组件

普通节点写法：

```svg
<g transform="translate(80 180)">
  <rect class="node" width="300" height="150" rx="8"/>
  <rect x="0" y="0" width="4" height="150" rx="2" fill="#2563EB"/>
  <text class="text-main" x="22" y="42" font-size="16" font-weight="700">节点标题</text>
  <text class="text-body" x="22" y="74" font-size="14">
    <tspan x="22" dy="0">第一行短句</tspan>
    <tspan x="22" dy="21">第二行短句</tspan>
  </text>
</g>
```

无强调色节点：

```svg
<g transform="translate(80 180)">
  <rect class="node" width="300" height="130" rx="8"/>
  <text class="text-main" x="20" y="40" font-size="16" font-weight="700">节点标题</text>
  <text class="text-body" x="20" y="72" font-size="14">一句核心说明</text>
</g>
```

编号徽章：

```svg
<g transform="translate(24 28)">
  <circle r="12" fill="#E2E8F0"/>
  <text class="text-main" text-anchor="middle" y="4" font-size="11" font-weight="700">1</text>
</g>
```

## 箭头规则

- 箭头端点停在节点边缘外 `2px` 到 `6px`，不要进入节点内部。
- 优先让箭头走节点之间的 gutter。路径不要穿过文字区域。
- 同层并列节点使用折线或二次贝塞尔曲线，避免斜线扫过内容。
- 主流程箭头可以用 `#2563EB`；其他关系默认用 `#475569` 或 `#64748B`。
- marker 颜色要和箭头 stroke 一致。需要新增语义色时，同步新增对应 marker。

横向箭头：

```svg
<path class="arrow" d="M 380 255 C 420 255, 440 255, 480 255" stroke="#2563EB" marker-end="url(#arrowPrimary)"/>
```

垂直箭头：

```svg
<path class="arrow" d="M 600 320 L 600 382" stroke="#475569" marker-end="url(#arrowNeutral)"/>
```

Fork 分叉：

```svg
<path class="arrow" d="M 600 250 L 600 300" stroke="#2563EB"/>
<path class="arrow" d="M 280 300 L 920 300" stroke="#2563EB"/>
<path class="arrow" d="M 280 300 L 280 350" stroke="#2563EB" marker-end="url(#arrowPrimary)"/>
<path class="arrow" d="M 600 300 L 600 350" stroke="#2563EB" marker-end="url(#arrowPrimary)"/>
<path class="arrow" d="M 920 300 L 920 350" stroke="#2563EB" marker-end="url(#arrowPrimary)"/>
```

## 布局选择

### Fork + 并列节点

适合表达一个入口拆成多个策略、模块、风险或结果。

- 根节点居中，2 到 4 个节点并列。
- 根节点到分叉横线的距离不小于 `36px`。
- 并列节点尺寸一致；颜色只用于区分必要语义。
- 分叉线放在节点上方 gutter，不贴节点标题。

### 垂直工作流

适合表达写作、构建、审核、降级兜底、上线流程。

- 左侧放编号和主线，右侧放步骤节点。
- 每步节点高度尽量一致；长步骤拆成两行正文。
- 降级或兜底节点可以用 Amber 或 Red 小标签，但不要用大片警告色。

### 分层架构

适合表达客户端、服务端、数据层、平台能力。

- 每层使用浅灰分组容器，内部放节点。
- 层与层之间用水平箭头或垂直箭头连接。
- 大容器标签放左上角，避免和内部节点标题抢层级。

### 泳道

适合表达多角色协作，如用户、前端、服务端、数据平台。

- 每条泳道一个横向 band，左侧固定角色名。
- 同一时间线从左到右推进。
- 跨泳道箭头只能在节点之间走，不穿过角色标签。

### 对比矩阵

适合表达方案 A/B/C、旧方案/新方案、风险/收益对照。

- 使用列标题 + 对比项结构。
- 每个单元格最多两行短句。
- 推荐项用 Green 小标签或细边框，风险项用 Red 小标签；不做大片彩色背景。

### 状态机

适合表达生命周期、状态跳转、异常回退。

- 状态节点统一尺寸，终态使用 Green 小标签，异常态使用 Red 小标签。
- 自环和回退箭头必须走节点外侧。
- 转换条件写在箭头旁边，标签和箭头至少 `8px` 间距。

## 文本换行

SVG 不会自动换行。写节点正文前先按节点宽度估算：

```text
可用宽度 = 节点宽度 - 左右 padding
中文每行最大字数 ≈ 可用宽度 / 字号
英文每行最大字符数 ≈ 可用宽度 / (字号 * 0.58)
```

不确定时宁可多一行，也不要压到边框。节点正文超过 3 行时，删减文字或拆分节点。

## 图层顺序

推荐顺序：

1. 背景。
2. 分组容器和泳道背景。
3. 连接线、箭头主干、分叉线。
4. 节点。
5. 节点内文字、编号、标签。
6. 需要覆盖在最上层的短标签或强调圈。

如果跨容器箭头被节点遮住，先调整路径走 gutter；仍无法解决时，把该箭头移到节点层之后，但端点必须停在边缘，且不能覆盖文字。
