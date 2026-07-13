# Obsidian Eval Fixtures

本目录保存 `obsidian` 的行为回归用例和故障注入材料，用于验证写作流程能否拦住结构、文风和跨载体一致性退化。

- `evals.json` 遵循仓库 skill eval schema；每个用例包含 prompt、预期输出、输入文件和可二元判断的 expectations。
- `fixtures/` 只提供任务原始材料，不提供目标成稿；任务 Agent 只能看到 prompt 和对应 files，不能看到 expectations。
- 使用 `run_evals.py prepare` 创建隔离的 Agent task、被测 skill 快照、grader rubric、submission 目录和输入/skill 哈希。只把 `agent/` 提供给 fresh Agent，让它从 `skill/SKILL.md` 开始执行；不把 `grader/` 暴露给任务执行者。
- Agent 把最终文档写到 `submission/final.md`，把 style profile、knowledge map、结构/文风两轮审查和命令输出写到 `submission/trace.md`，附件写到 `submission/assets/`；trace 是评测证据，不写入最终笔记。
- grader 根据 rubric 的 expectations 逐项判定，在 `assessment-template.json` 中填写 boolean 结果和 `submission/...:line` 证据。`run_evals.py finalize` 校验 expectation 完整性、输入哈希和证据路径，并持久化 `grader/result.json`。
- 修改 skill 前后使用相同 eval id 运行；`input_sha256` 应一致，`skill_sha256` 用于标识被测版本，输出写到不同临时目录，避免前一轮产物污染后一轮。

```bash
python3 skills/obsidian/evals/run_evals.py prepare \
  --eval-id 8 \
  --run-dir /tmp/obsidian-eval-8

# 用 fresh Agent 执行 /tmp/obsidian-eval-8/agent/task.json，只允许读取 agent/、写 submission/。
# grader 完成 grader/assessment.json 后归档结果：
python3 skills/obsidian/evals/run_evals.py finalize \
  --run-dir /tmp/obsidian-eval-8 \
  --assessment /tmp/obsidian-eval-8/grader/assessment.json
```

仓库不绑定具体模型调用器，但任务包、输入哈希、产物结构、评分证据和结果归档是确定的。`scripts/validate-plugin.py` 校验 eval schema 与 fixture 路径，两个 `test_*.py` 分别负责 validator 和 eval harness 回归。
