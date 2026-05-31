---
name: lite-diff-marker
version: 0.1.2
tags: [android, lite, diff, marker]
description: 矩阵产品差异化标记助手，仅当用户明确要求添加差异化标记、补 Lite 标记、按矩阵差异化规范处理 diff，或使用 @LiteAdd/@LiteModified/@LiteDelete/@BaseSplit 时触发。不要因普通 Android 代码修改、diff 查看或代码 review 触发。
user_invocable: true
---

# 矩阵差异化标记

## 目标

帮助用户把 Android 手百基线代码与矩阵差异化改动按 V3.0 规范补齐标记，避免基线升级合并时丢失矩阵代码。

处理对象包括：

- Java / Kotlin 文件、类、方法、字段、属性和局部代码片段
- XML 文件和 XML 代码片段
- Gradle、ProGuard、脚本配置等使用 `#` 注释的文本片段

## 触发边界

### 适用

用户明确要求"添加差异化标记""补 Lite 标记""按矩阵差异化规范处理 diff"，或点名 `@LiteAdd`、`@LiteModified`、`@LiteDelete`、`@BaseSplit` 等标记。

### 不适用

用户只是要求普通 Android 修改、查看 diff、解释代码、修 bug、review 代码，且没有提到矩阵差异化或 Lite 标记时，不使用本技能。

### 需要确认

如果用户给了文件路径或 diff，但没有说明这是矩阵差异化改动，先确认是否需要实际加标记；如果只要求预览，不要直接编辑文件。

## 输入识别

用户可能提供以下任意一种输入：

- 一个或多个文件路径，要求"加差异化标记"
- 当前仓库的 `git diff` / 未提交改动
- 修改前和修改后的代码片段
- 只贴出一段代码，并说明这是新增、修改或删除

如果用户给了文件路径或当前仓库改动，优先直接编辑文件。  
如果用户只贴代码片段，直接输出补好标记的代码块。  
如果无法判断改动属于新增、修改还是删除，先查看 `git diff`、相邻代码和文件历史；仍无法判断时，向用户确认，不要盲目套标记。

## 工作流程

1. **定位改动**
   - 使用 `git diff`、用户提供的 before/after、或文件内容定位真实差异。
   - 用户给出具体文件行号但没有 before/after 时，必须查看 `git log`、`git show` 或 `git blame`，从提交历史确认该行相对手百基线是新增、修改还是删除；不要只凭当前代码猜类型。
   - 按最小可维护范围打标，避免把无关代码包进同一个标记块。

2. **判断类型**（详细规则见 `references/marking-rules.md`）
   - 新增：手百基线中没有对应逻辑，矩阵侧新增逻辑 → `@LiteAdd`
   - 修改：手百基线已有逻辑，矩阵侧替换为另一段逻辑 → `@BaseSplit` + `@LiteModified`
   - 删除：屏蔽手百基线逻辑，矩阵侧没有替代逻辑 → `@LiteDelete`

3. **选择注释语法**
   - Java / Kotlin：块注释 `/* ... */` 和注解
   - XML：`<!-- ... -->`
   - Gradle / ProGuard / shell / Python：`#`

4. **补充描述**
   - 标记描述要短、具体，说明"为什么差异化"或"改动点是什么"。
   - 不要留空描述；不要写泛泛的"修改逻辑""新增代码"。

5. **校验结果**
   - 每个开始标记都必须有结束标记。
   - 不改变业务逻辑、缩进风格和原有格式。
   - Java / Kotlin 中不要制造嵌套块注释。
   - 新增注解时按项目已有写法补 import（查找方法见 `references/marking-rules.md`）。

## Progressive Disclosure

需要具体标记语法、代码示例或 import 处理方法时，读取：

- `references/marking-rules.md`：Java/Kotlin、XML、脚本配置的完整规则和代码示例

## 输出要求

完成后给用户说明：

- 处理了哪些文件或片段。
- 每类改动使用了哪些标记。
- 是否有无法自动判断的片段。
- 是否运行了格式化、编译或测试；如果没有运行，要说明原因。

不要把整份规范原文重复给用户；只报告本次改动结果和必要注意事项。
