# Front Matter 与发布形态

Vault 内所有新增或修改的正文笔记都必须以 YAML front matter 开头。目标目录存在更具体规范时，以局部规范为准。

## 博客文章

`type: post` 进入博客流，必填字段如下：

```yaml
---
publish: true
type: post
title: Agent Skills 完全指南
date: 2026-07-09
summary: 用一两句话说明文章解决什么问题，以及读者为什么要看。
tags: [AI, Agent, Engineering]
---
```

规则：

- `title` 使用正式标题，通常与文件名一致。
- `date` 使用真实的 `YYYY-MM-DD` 日期，不写相对日期。
- `summary` 写清文章价值，不保留 `...`、`TODO`、`TBD` 或模板占位符。
- `tags` 使用非空行内数组。

## 普通笔记

`type: note` 进入公开笔记库或作为私有笔记保存：

```yaml
---
publish: true
type: note
topic: AI
---
```

尚未整理完成或不公开时显式写：

```yaml
---
publish: false
type: note
topic: AI
---
```

`topic` 使用稳定主题，例如 `AI`、`Android`、`Network`，不要使用一次性任务名。

## 修改旧文

- 保留不了解用途的已有字段、aliases、cssclasses 和站点扩展字段。
- 不因为切换模板而重排全部 front matter。
- 旧文没有 front matter 且无法判断发布形态时，补 `publish: false`、`type: note` 和合适的 `topic`。
- 只有用户明确要改变发布状态时，才修改现有 `publish`。

## 模板使用

`assets/templates/` 中的 `{{...}}` 是生成期占位符。复制模板后必须全部替换，并在交付前运行 validator；不要把占位符写进 Vault。
