# Problem Diagnosis Notes

问题：Android 详情页偶现白屏，用户点击消息 push 进入详情后停留在 loading。

复现条件：

- 版本：8.7.0-beta2。
- 入口：push 通知 -> 详情页。
- 网络：弱网或首次冷启动更容易复现。

已确认事实：

- `DetailActivity` 收到 intent 后调用 `loadDetail()`。
- 日志中出现 `detail_id` 为空，但 push payload 里有 `detailId` 字段。
- 最近一次改动把 schema 参数从 snake_case 改成 camelCase。

待验证：

- 是否所有 push 模板都已经切到 `detailId`。
- 是否存在 deeplink 仍使用旧参数。

初步修复方向：

- 解析层同时兼容 `detail_id` 和 `detailId`。
- 缺失 detail id 时不要一直 loading，应展示错误态并打点。
