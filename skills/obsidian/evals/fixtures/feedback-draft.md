---
publish: false
type: note
topic: Orbit Plugin
---
## 定义与边界
Orbit Plugin 是本地目录包，不是常驻服务。
## 先用一句话认识加载流程
Orbit 在启动时扫描插件目录，然后校验 manifest 并注册组件。
## 组成部分到底长什么样
manifest 声明插件名和版本，skills 保存能力定义。

| 先看哪里 | 作用 |
| --- | --- |
| manifest | 你可以先用它确认插件身份 |

> 最重要的不是扫描，而是真正好用的注册流程。

```jsonc
{
  // 回到刚才的例子，你可以先填写名称
  "name": "hello-orbit",
  "version": "1.0.0"
}
```
## 运行机制
正文把第一阶段统一称为“扫描”，图中应使用相同术语。
![[img/orbit-runtime.svg|760]]
![[img/missing-overview.png|760]]
## 排错
先检查 manifest 校验结果，再检查组件注册日志。

---
## 相关笔记
