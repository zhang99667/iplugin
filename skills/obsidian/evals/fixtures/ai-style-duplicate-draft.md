---
publish: false
type: note
topic: Orbit Plugin
---
## 先用一句话认识 Orbit Plugin
Orbit Plugin 最重要的不是目录，而是把能力作为一个包加载。总之，它解决的是统一管理问题。
## Orbit Plugin 到底长什么样
你可以先看一个最小目录。真正好用的 Plugin 都会包含 manifest，值得注意的是，manifest 是加载入口。

| 到底要看什么 | 真正重要的内容 |
| --- | --- |
| manifest | 最重要的不是文件名，而是加载入口 |

> 回到刚才的例子，你可以发现 manifest 是加载入口。

```jsonc
{
  // 你可以先记住：manifest 是加载入口
  "name": "hello-orbit",
  "version": "1.0.0"
}
```
## 真正好用的加载流程
从某种意义上说，Orbit 会扫描、校验并注册。manifest 是加载入口，也是整个流程最重要的起点。
## 到底怎么选
Orbit Desktop 支持 hooks，Orbit Web 不支持 hooks。显然 Desktop 是更完整、更专业的选择。
## 核心结论
manifest 是加载入口。最重要的不是目录，而是 manifest。总之，先看 manifest 就够了。

---
## 相关笔记
