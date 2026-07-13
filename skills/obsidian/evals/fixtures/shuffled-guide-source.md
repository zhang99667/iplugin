# Orbit Plugin 评测资料

本文是唯一事实来源，段落顺序被故意打乱。`Orbit Plugin` 是评测用虚构系统，不得用外部常识补充事实。

## 不同产品中的实现

- Orbit Desktop 支持 manifest、skills 和 hooks。
- Orbit Web 只读取 manifest 与 skills，忽略 hooks。

## 设计、安全与排错

- loader 拒绝越出插件根目录的相对路径。
- hook 执行前必须获得用户授权。
- 排错时先看 manifest 校验结果，再看组件注册日志。

## 组成部分

- `plugin.json`：必需，声明插件名与版本。
- `skills/`：可选，保存可发现的能力定义。
- `hooks/`：可选，保存事件触发配置。

## 为什么需要

Orbit 原本要求用户分别复制能力文件和 hook 配置。Plugin 把这些文件作为一个可启用、停用和升级的目录包管理，减少多处手工同步。

## 定义与边界

Orbit Plugin 是一个本地目录包，至少包含 `plugin.json`。它不是常驻服务，也不负责从网络下载自身依赖。

## 加载和运行机制

Orbit 在启动时扫描已配置的插件根目录，校验 manifest，再注册当前产品支持的组件。被停用的插件不会进入注册阶段；修改文件后需要重新启动才会生效。

## 最小可运行示例

最小目录只需要 manifest：

```text
hello-orbit/
└── plugin.json
```

```json
{
  "name": "hello-orbit",
  "version": "1.0.0"
}
```

启动日志出现 `registered plugin: hello-orbit` 表示示例加载成功。

## 必须覆盖的知识点

定义与边界、存在理由、最小可运行示例、组成部分、加载和运行机制、Desktop/Web 差异、路径安全、hook 授权、排错顺序。
