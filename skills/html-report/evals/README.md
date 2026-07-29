# html-report Eval Fixtures

本目录保存 `html-report` 的回归用例定义和输入 fixture，用于发现报告整体质量退化。

- `evals.json` 遵循 skill-creator 的 eval schema：每个用例包含 prompt、期望输出、输入文件和可检查 expectations。
- `fixtures/` 保存真实 prompt 会附带的最小输入材料，例如 diff、日志、验收 case 和待注入批注的普通 HTML。
- Review Workspace 回归同时覆盖 `review_workspace_spec.json` 三方模式和 `review_workspace_two_way_spec.json` 二方模式，验证同一构建脚本会按 2–3 个版本自动布局，且组件结构与安全转义不会退化。
- `knowledge-guide-structure-preservation` 覆盖已有知识文档的结构保真，防止内容覆盖清单退化成固定目录，同时检查代码片段、锚点和来源没有遗漏。
- `component-stability-table-and-multi-file-diff` 覆盖普通表格完整网格线和多文件 patch 每文件独立 Diff 卡片，防止组件装配再次依赖模型临场发挥。
- `run_evals.py run` 使用两个独立的临时 Codex 会话完成任务和评分：任务 Agent 只能看到 prompt、fixtures 和 skill 快照；完成任务后才生成 grader rubric，避免 expectations 泄露。
- Runner 会先运行快照中的 `check_html_report.py`，再由 grader 逐项给出 boolean 结果和 `submission/...:line` 证据，最终记录单次 expectation 通过率；`summary` 可汇总多个运行目录。
- `prepare`、`verify`、`finalize` 提供分阶段入口，便于人工或其他 fresh Agent 接管，同时用输入、skill 和提交物哈希阻止跨轮污染。
- `scripts/validate-plugin.py` 会校验 `evals.json` 的基础结构和 fixture 路径，避免用例断链。

新增 html-report 能力时，优先补充一个对应 eval，再调整模板或脚本。

完整自动运行会产生一次任务调用和一次 grader 调用，只用于 skill 维护与版本验收，不进入普通 HTML 报告生成流程：

```bash
python3 skills/html-report/evals/run_evals.py run \
  --eval-id 1 \
  --run-dir /tmp/html-report-eval-1

python3 skills/html-report/evals/run_evals.py summary \
  --runs-dir /tmp/html-report-evals \
  --output /tmp/html-report-evals/summary.json
```

需要手动调度 fresh Agent 时使用分阶段流程：

```bash
python3 skills/html-report/evals/run_evals.py prepare --eval-id 1 --run-dir /tmp/html-report-eval-1
# Agent 只读取 agent/，并按 TASK.md 写入 submission/。
python3 skills/html-report/evals/run_evals.py verify --run-dir /tmp/html-report-eval-1
# grader 按 grader/rubric.json 填写 assessment.json。
python3 skills/html-report/evals/run_evals.py finalize \
  --run-dir /tmp/html-report-eval-1 \
  --assessment /tmp/html-report-eval-1/grader/assessment.json
```
