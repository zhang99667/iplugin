---
description: Generate an HTML report from the current answer, previous answer, or provided context.
argument-hint: [content-or-instructions]
user_invocable: true
arguments:
  - name: args
    description: "可选：需要整理成 HTML 报告的内容、上下文或输出要求"
    required: false
---

# /htmlreport

## Arguments

The user invoked this command with: `$ARGUMENTS`

## Instructions

When this command is invoked:

1. Read and follow `skills/html-report/SKILL.md`.
2. Use `$ARGUMENTS` as the primary report source or report requirement.
3. If `$ARGUMENTS` is empty, infer the report source from the immediately preceding answer, conclusion, review result, investigation notes, or current task context.
4. Treat the command invocation as an explicit HTML request: generate HTML directly and do not ask whether Markdown is preferred.
5. Preserve the skill's content-type judgment: formal technical/business documents and analysis reports need a document header; ordinary conversation exports stay lightweight.
6. Use the default output path from the skill when the user does not specify a path.
7. After generating the file, reply only with the file path and one short summary sentence.

If there is not enough source material to produce a meaningful report, ask one concise clarification question instead of creating a placeholder page.
