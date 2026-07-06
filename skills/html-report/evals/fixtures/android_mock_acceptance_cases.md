# Android Mock Acceptance Cases

需求：验证商品详情页优惠券 mock 链路。

环境：

- App：debug build `8.8.0-mock-20260706`。
- 设备：Pixel 7 / Android 15。
- mockserver：`http://127.0.0.1:8088`。
- scheme：`baiduboxapp://goods/detail?id=10086&mock=1`。

Case 矩阵：

| Case | 场景 | 步骤 | 预期 | 实际 | 结果 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| AC-01 | 有券可领 | 打开 scheme，等待接口返回 | 展示“立即领取”按钮，mockserver 命中 `/coupon/list` | UI 符合预期，日志显示 200 | 通过 | 截图待补，mockserver 日志已提供摘要 |
| AC-02 | 无券 | 切换 mock case `empty_coupon` 后打开页面 | 不展示按钮，展示普通价格区 | UI 符合预期 | 通过 | 录屏待补 |
| AC-03 | 接口失败 | 切换 mock case `coupon_500` | 不崩溃，展示无券兜底，日志有错误码 | 未执行 | 未测 | 待补 |
| AC-04 | 弱网 loading | 限速后打开页面 | loading 不超过 3 秒，有失败兜底 | 出现 5 秒 loading | 失败 | 日志摘要显示 timeout |

mockserver 摘要：

```text
GET /coupon/list?goodsId=10086 -> 200 case=default hit=1
GET /coupon/list?goodsId=10086 -> 200 case=empty_coupon hit=1
GET /coupon/list?goodsId=10086 -> not requested case=coupon_500
```

注意：当前没有真实截图或录屏文件，生成报告时只能做占位，不要引用不存在的 `png`、`mp4` 路径。
