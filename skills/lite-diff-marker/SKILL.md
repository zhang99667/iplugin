---
name: lite-diff-marker
version: 0.1.0
tags: [android, lite, diff, marker]
description: 矩阵产品差异化标记助手。当用户要求“添加差异化标记”“补 Lite 标记”“按矩阵差异化规范处理 diff”“给手百/极速版/矩阵改动加 @LiteAdd/@LiteModified/@LiteDelete/@BaseSplit”时触发。根据 Android Java/Kotlin、XML 和脚本配置改动类型，选择新增、修改、删除标记并直接修改代码或输出可应用 patch。
user_invocable: true
---

# 矩阵差异化标记

## 目标

帮助用户把 Android 手百基线代码与矩阵差异化改动按 V3.0 规范补齐标记，避免基线升级合并时丢失矩阵代码。

处理对象包括：

- Java / Kotlin 文件、类、方法、字段、属性和局部代码片段
- XML 文件和 XML 代码片段
- Gradle、ProGuard、脚本配置等使用 `#` 注释的文本片段

## 输入识别

用户可能提供以下任意一种输入：

- 一个或多个文件路径，要求“加差异化标记”
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

2. **判断类型**
   - 新增：手百基线中没有对应逻辑，矩阵侧新增逻辑。
   - 修改：手百基线已有逻辑，但矩阵侧替换为另一段逻辑。
   - 删除：屏蔽手百基线逻辑，矩阵侧没有替代逻辑。
   - 新增行只使用 `@LiteAdd`，不要为了补 `@BaseSplit` 写空基线块。
   - 只标记实际发生变化的最小片段。单行参数、字段、调用参数变化时，只包这一行或这一条语句；不要把整个方法、构造函数或 class 签名一起包住。

3. **选择注释语法**
   - Java / Kotlin 使用块注释 `/* ... */` 和注解。
   - XML 使用 `<!-- ... -->`。
   - Gradle、ProGuard、shell、Python 等脚本配置优先使用 `#`。
   - 未列出的文件类型按文件自身注释语法选择最接近的规则。

4. **补充描述**
   - 标记描述要短、具体，说明“为什么差异化”或“改动点是什么”。
   - 不要留空描述；不要写泛泛的“修改逻辑”“新增代码”。
   - 注解类标记使用 `desc = "..."`；代码块标记把描述写在起始标记后。

5. **校验结果**
   - 每个开始标记都必须有结束标记。
   - 不改变业务逻辑、缩进风格和原有格式。
   - Java / Kotlin 中不要制造嵌套块注释。
   - 新增注解时按项目已有写法补 import；不能确定注解包名时先查同仓库已有用法。

## Java / Kotlin 规则

### 新增文件、类、方法、字段

优先使用语义注解，而不是整段块注释。

| 对象 | 标记 |
| --- | --- |
| 新增 Kotlin 文件，且只有顶层函数或属性 | `@file:LiteClass(desc = "...")` |
| 新增类 | `@LiteClass(desc = "...")` |
| 新增方法 | `@LiteMethod(desc = "...")` |
| 新增 Java 字段 / Kotlin 普通属性 | `@LiteField(desc = "...")` |
| 新增 Kotlin 自定义 getter 或委托属性 | `@get:LiteMethod(desc = "...")` |

示例：

```kotlin
@LiteMethod(desc = "新增短小融合沉浸式转场精控")
fun circleTransitionRefine(): Int {
    return 0
}
```

Kotlin 属性选择规则：

- 直接赋值属性、构造函数 `val/var` 参数、枚举字段：使用 `@LiteField`。
- 自定义 getter、委托属性：使用 `@get:LiteMethod`，因为 JVM 编译后 getter 是方法。

### 新增局部代码片段

```kotlin
/* @LiteAdd 更新超级开屏展示状态 */
if (isSuperSlash) {
    isSuperSlashShowing = true
}
/* @LiteAdd~ */
```

新增单行参数、字段或资源项也按局部新增处理，只包新增行本身：

```kotlin
open class NadFlowSummaryButtonHelper(
    private val store: Store<AbsState>?,
    model: NadGeneralButtonModel,
    /* @LiteAdd Lite v7.5.0 719 前卡通用按钮颜色兜底依赖 context */
    private val context: Context,
    /* @LiteAdd~ */
    private val callback: IOnEnhanceBtnShowCallBack? = null
)
```

注意：项目规范使用 `@LiteAdd` / `@LiteAdd~`，不要写成 `@LiteAdded`。

### 修改代码片段

保留手百基线代码在 `@BaseSplit` 块中，矩阵替代代码紧跟其后，并用 `@LiteModified` 包裹。

```kotlin
/* @BaseSplit
println("手百基线代码")
   @BaseSplit~ */
/* @LiteModified 输出矩阵日志 */
println("矩阵代码")
/* @LiteModified~ */
```

适用范围包括方法体、方法签名、类继承关系、修饰符、字段类型或初始化值等。

注意：Java / Kotlin 不支持嵌套块注释。如果基线片段内部已有 `/* ... */`，不要把该注释块包进 `@BaseSplit` 或 `@LiteDelete` 块注释；应只标记实际改动语句，必要时拆成多个小片段。

修改调用参数时，只标记被替换的调用语句，不要包裹外层 `if`、`apply` 后续属性设置或整个方法：

```kotlin
/* @BaseSplit
mGeneralButtonView = NadGeneralBtnManagerView(context, NadFlowSummaryButtonHelper(store, model, callback)).apply {
@BaseSplit~ */
/* @LiteModified Lite v7.5.0 719 前卡通用按钮 helper 增加 context 参数 */
mGeneralButtonView = NadGeneralBtnManagerView(context, NadFlowSummaryButtonHelper(store, model, context, callback)).apply {
/* @LiteModified~ */
    id = R.id.video_flow_ad_general_button
}
```

### 删除代码片段

```kotlin
/* @LiteDelete 屏蔽沉浸式首页视频手势引导
add(FlowVideoScaleGestureUnit.createReducer())
   @LiteDelete~ */
```

### 裁剪类

类仍需保留以满足编译或接口依赖，但内部逻辑被裁剪时，给类声明加 `@LiteDelete`，类内部按编译需要保留空实现或兜底返回。

```java
@LiteDelete(desc = "弹幕库被裁剪")
public class TalosDanmakuSource {
    public ParamArray data() {
        return null;
    }
}
```

## XML 规则

### 新增 XML 文件

在 XML 声明之后、根节点之前添加 `@LiteClass`。

```xml
<?xml version="1.0" encoding="utf-8"?>
<!-- @LiteClass -->
<shape xmlns:android="http://schemas.android.com/apk/res/android">
    <solid android:color="#FFFFFF" />
</shape>
```

### 新增 XML 片段

```xml
<!-- @LiteAdd 新增色值 -->
<solid android:color="#FFFFFF" />
<!-- @LiteAdd~ -->
```

### 修改 XML 片段

XML 修改不需要区分基线和矩阵两段代码，直接包裹修改后的完整 tag。

```xml
<!-- @LiteModified 修改布局尺寸并居中展示 -->
<TextView
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:gravity="center" />
<!-- @LiteModified~ -->
```

### 删除 XML 片段

删除 XML 时保留被删 tag 的注释形态，外层使用 `@LiteDelete`。

```xml
<!-- @LiteDelete 无网盘上传功能 -->
<!-- <com.baidu.searchbox.download.center.ui.DownloadUploadNetdiskView -->
<!--     android:layout_width="wrap_content" -->
<!--     android:layout_height="wrap_content" /> -->
<!-- @LiteDelete~ -->
```

## 脚本配置规则

适用于 ProGuard、Gradle 配置片段、shell、Python 等使用 `#` 注释的场景。

### 新增

```text
# @LiteAdd 新增账号模块 keep 规则
-keep class com.baidu.searchbox.account.BoxAccountManager { *; }
# @LiteAdd~
```

### 修改

```text
# @LiteModified 针对所有函数全量 keep
# void setTextColorRes(android.widget.TextView,int);
# @BaseSplit
public protected *;
# @LiteModified~
```

### 删除

```text
# @LiteDelete Kotlin 按需 keep
# -dontwarn kotlin.**
# -keepclassmembers class **$WhenMappings {
#     <fields>;
# }
# @LiteDelete~
```

## Import 处理

新增 Java / Kotlin 注解时，先在仓库中搜索已有用法：

```bash
rg "@Lite(Class|Method|Field|Delete)|import .*Lite(Class|Method|Field|Delete)" .
```

按项目已有包名补 import。常见写法类似：

```kotlin
import com.baidu.searchbox.lite.annotation.LiteClass
import com.baidu.searchbox.lite.annotation.LiteMethod
import com.baidu.searchbox.lite.annotation.LiteField
import com.baidu.searchbox.lite.annotation.LiteDelete
```

不要在没有证据时臆造新的注解包名；如果仓库中没有任何已有用法，向用户确认或在最终说明中明确需要补齐注解依赖。

## 输出要求

完成后给用户说明：

- 处理了哪些文件或片段。
- 每类改动使用了哪些标记。
- 是否有无法自动判断的片段。
- 是否运行了格式化、编译或测试；如果没有运行，要说明原因。

不要把整份规范原文重复给用户；只报告本次改动结果和必要注意事项。
