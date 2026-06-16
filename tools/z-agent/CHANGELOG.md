# 变更日志

## 0.1.0

版本记录：`versions/v0.1.0.md`

### 新增

- 新增初版 `zagent` CLI 子项目。
- 新增带锁和原子写入的 workspace 状态存储。
- 新增 Codex 和 Claude Code 的 Agent 配置。
- 新增 hook ingest，用于写入会话元数据。
- 新增安全恢复计划，执行前校验结构化命令白名单。
- 新增安装能力，并生成 Agent hook 相关文件。
- 新增 Ghostty 采集/恢复适配层，恢复前仍执行结构化命令白名单校验。
- 新增覆盖状态、钩子、包装器上下文、恢复计划和 Agent 配置的单元测试。

### 优化

- 补充 `AgentSpec` 和 `WrapperContext` 的字段级中文说明，降低阅读和审阅成本。
- 重写 README 的使用流程，补充安装、钩子合并、启动智能体、采集快照、恢复和排障说明。
- 收敛命令行参数，`snapshot capture` 只负责采集，`restore` 只负责恢复。

### 修复

- 修复命令行主入口调用解析器时的拼写错误，恢复 `zagent doctor` 等普通子命令。
