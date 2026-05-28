---
description: Manually hand the current uncertainty to AskUserQuestion.
argument-hint: [question-or-context]
user_invocable: true
arguments:
  - name: args
    description: "可选：需要让用户选择的问题、背景或方案"
    required: false
---

# /askuserquestion

## Arguments

The user invoked this command with: `$ARGUMENTS`

## Instructions

When this command is invoked:

1. Read and follow `skills/ask-user-question/SKILL.md`.
2. Use `$ARGUMENTS` as the primary decision context.
3. If `$ARGUMENTS` is empty, infer the decision point from the immediately preceding task context.
4. Prefer the environment's structured user-question tool, such as `AskUserQuestion` or `request_user_input`.
5. If the structured tool is unavailable, fall back to the plain-text choice format defined in the skill.

Do not solve the underlying task before the user chooses. The purpose of this command is to pause at the uncertainty and collect a concrete user decision.
