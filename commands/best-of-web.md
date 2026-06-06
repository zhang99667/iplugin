---
description: Explicitly invoke the best-of-web skill to search excellent public sources and synthesize the best available content.
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

1. Treat this slash command as the explicit activation path for the `best-of-web` skill.
2. Use the `best-of-web` skill and execute its research workflow; do not merely summarize, display, or inspect `skills/best-of-web/SKILL.md`.
3. Use `$ARGUMENTS` as the primary topic, question, or output requirement.
4. If `$ARGUMENTS` is empty, infer the research target from the immediately preceding user request or conversation context.
5. If the target is still unclear, ask one concise clarification question before searching.
