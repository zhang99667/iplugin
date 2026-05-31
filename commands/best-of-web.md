---
description: Search the web for excellent sources and synthesize the best available content.
argument-hint: [topic-or-question]
user_invocable: true
arguments:
  - name: args
    description: "可选：需要联网搜索、精选和整合的主题、问题或输出要求"
    required: false
---

# /best-of-web

## Arguments

The user invoked this command with: `$ARGUMENTS`

## Instructions

When this command is invoked:

1. Read and follow `skills/best-of-web/SKILL.md`.
2. Treat the command invocation as an explicit `best-of-web` request.
3. Use `$ARGUMENTS` as the primary topic, question, or output requirement.
4. If `$ARGUMENTS` is empty, infer the research target from the immediately preceding user request or conversation context.
5. If the target is still unclear, ask one concise clarification question before searching.
