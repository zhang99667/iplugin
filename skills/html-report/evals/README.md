# html-report Eval Fixtures

本目录保存 `html-report` 的回归用例定义和输入 fixture，用于发现报告整体质量退化。

- `evals.json` 遵循 skill-creator 的 eval schema：每个用例包含 prompt、期望输出、输入文件和可检查 expectations。
- `fixtures/` 保存真实 prompt 会附带的最小输入材料，例如 diff、日志、验收 case 和待注入批注的普通 HTML。
- Review Workspace 回归同时覆盖 `review_workspace_spec.json` 三方模式和 `review_workspace_two_way_spec.json` 二方模式，验证同一构建脚本会按 2–3 个版本自动布局，且组件结构与安全转义不会退化。
- `knowledge-guide-structure-preservation` 覆盖已有知识文档的结构保真，防止内容覆盖清单退化成固定目录，同时检查代码片段、锚点和来源没有遗漏。
- `component-stability-table-and-multi-file-diff` 覆盖普通表格完整网格线和多文件 patch 每文件独立 Diff 卡片，防止组件装配再次依赖模型临场发挥。
- 当前仓库不内置模型执行器；运行回归时可以用 skill-creator 或外部 runner 逐条执行 prompt，再按 expectations 评估输出。
- `scripts/validate-plugin.py` 会校验 `evals.json` 的基础结构和 fixture 路径，避免用例断链。

新增 html-report 能力时，优先补充一个对应 eval，再调整模板或脚本。
