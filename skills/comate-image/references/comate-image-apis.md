# Comate 图片生成接口摘要

鉴权统一使用：

```http
Authorization: Bearer <COMATE_API_KEY>
Content-Type: application/json
```

## 链路对比

| backend | Endpoint | 默认模型 | 请求关键字段 | 图片 base64 路径 | 使用建议 |
| --- | --- | --- | --- | --- | --- |
| `images` | `/v1/images/generations` | `gpt-image-2` | `prompt`, `size`, `n` | `data[0].b64_json` | 默认首选，结构最直接 |
| `responses` | `/v1/responses` | `gpt-5.5` | `input`, `tools:[{type:"image_generation"}]` | `output[*].result` 中的 `image_generation_call` | 已在 Responses 编排工具时使用；502 可重试 |
| `banana` | `/v1beta/models/{model}:generateContent` | `gemini-3.1-flash-image-preview` | `contents`, `generationConfig.responseModalities` | 首个 `inlineData.data` | 需要 Banana/Gemini 兼容链路时使用 |

## 默认命令

```bash
python3 skills/comate-image/scripts/comate_image_client.py images \
  --prompt "写实风格，一位程序员坐在电脑前吃泡面，不要文字和水印" \
  --stem "程序员夜晚泡面" \
  --out-dir ./outputs
```

可选链路：

```bash
python3 skills/comate-image/scripts/comate_image_client.py responses \
  --prompt "..." \
  --stem "..."

python3 skills/comate-image/scripts/comate_image_client.py banana \
  --prompt "..." \
  --stem "..."
```

CLI 也接受常用别名：`gptimg2` / `gpt-image-2` 等同于 `images`，`banana2` 等同于 `banana`。默认会从 `--prompt` 开头或结尾剥离 `Comate`、`banana2`、`gptimg2`、`生成图片`、`出图`、`prompt 是` 等路由词；只有确实要把这些词画进图片时，才加 `--raw-prompt`。

## 输出

脚本会打印：

```text
saved: <path>
mime: image/png
bytes: <decoded image bytes>
response_path: <base64 field path>
```

如果 `--out` 没有扩展名，脚本按 MIME 自动补 `.png` / `.jpg` 等扩展名；如果未提供 `--out`，脚本使用 `--stem` 或 prompt 生成语义化文件名，并在重名时追加数字后缀。

## 错误处理

- 缺少 key、HTTP 401、HTTP 403：视为认证错误，使用 `ask-user-question` 询问用户设置或刷新 key。
- HTTP 502 / upstream overload：原 prompt 不变重试一次。
- 响应里找不到图片 base64：报告 backend、模型和错误摘要，必要时切换到 `images` 链路复测。
- 不要把 token 打印到日志里；错误摘要只保留 HTTP 状态和服务端错误信息。
