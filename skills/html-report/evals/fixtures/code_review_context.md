# Code Review Context

仓库：`example/mobile-feed`

变更目标：在 feed 详情页加载失败时展示兜底文案，并把 Objective-C bridge 的错误码透传到前端。

评审重点：

- 新增错误码是否会覆盖已有成功态。
- Objective-C bridge 的回调是否可能重复触发。
- 失败态是否有单测或手动验证证据。

已知约束：

- `FeedDetailViewModel` 的 `state` 由 UI 层直接观察。
- `FeedBridge.m` 的 completion 可能在主线程或后台线程回调。
- 当前 diff 只提供核心片段，不要假设其他文件已经修复。
