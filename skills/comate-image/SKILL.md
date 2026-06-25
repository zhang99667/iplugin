---
name: comate-image
version: 0.1.0
description: Comate 图片生成助手。当用户要求使用 Comate、Comate Image API、oneapi-comate、gpt-image-2、gpt-5.5 image_generation、Banana/Gemini 图片接口生成图片，或要求“用 Comate 生成图片”“跑 comate_image_client”“根据 prompt 出图”时触发；内置标准库客户端，自动为输出图片选择语义化文件名，并在 COMATE_API_KEY 缺失或过期时使用 ask-user-question 询问用户提供或刷新密钥。
tags: [comate, image, image-generation, api, baidu, gpt-image, banana]
---

# Comate 图片生成

目标：通过 Comate 兼容图片接口生成图片，并把鉴权、接口选择、输出命名和本地保存做成稳定流程。

## 触发边界

### 适用

- 用户明确提到 Comate、Comate Image API、oneapi-comate、`comate_image_client.py`、`gpt-image-2`、`gpt-5.5 image_generation`、Banana/Gemini 图片接口。
- 用户要求“用 Comate 生成图片”“跑图片 API”“根据这个 prompt 出图”“保存生成图片到本地”。
- 用户提供图片生成 prompt，希望把输出保存为本地文件，并需要自动判断语义化文件名。

### 不适用

- 用户只要求普通 OpenAI 图像生成或编辑，且没有提到 Comate；优先使用平台内置图像生成能力。
- 用户要真实网页截图、Figma 设计或 SVG 技术图；分别使用浏览器/Figma/SVG 相关能力。
- 用户要求图片后处理、批量压缩、抠图或格式转换，且不需要调用 Comate 出图。

## 执行流程

1. 提炼 prompt。
   - 保留用户的主体、场景、风格、构图、比例、禁止文字/水印等要求。
   - 不擅自加入品牌、人名、敏感信息或用户未要求的元素。
2. 选择链路。
   - 默认使用 `images`，模型 `gpt-image-2`，结构最直接。
   - 用户明确要 Responses 编排或工具链路时用 `responses`，模型 `gpt-5.5`。
   - 用户明确要 Banana/Gemini 兼容链路时用 `banana`，模型 `gemini-3.1-flash-image-preview`。
   - 需要接口细节时读取 `references/comate-image-apis.md`。
3. 判断输出名。
   - 不使用 `out.png`、`image.png`、`test.png` 这类泛名。
   - 根据 prompt 的主体、动作、场景或用途取 3 到 8 个语义词；中文 prompt 可用中文文件名，英文 prompt 用 kebab-case。
   - 只在对比多条链路时把 backend 或模型名放入文件名，例如 `programmer-noodles-images.png`。
   - 优先把语义名传给脚本的 `--stem`，让脚本自动补扩展名和避让重名文件。
4. 执行生成。
   - 使用内置脚本：`skills/comate-image/scripts/comate_image_client.py`。
   - 默认命令形态：

```bash
python3 skills/comate-image/scripts/comate_image_client.py images \
  --prompt "写实风格，一位程序员坐在电脑前吃泡面，不要文字和水印" \
  --stem "程序员夜晚泡面" \
  --out-dir ./outputs
```

5. 校验结果。
   - 命令输出必须包含 `saved:`、`mime:`、`bytes:` 和 `response_path:`。
   - 如果生成图片用于交付，打开或读取图片确认文件存在、大小非 0、格式正确。
   - 如果接口返回 502 或上游过载，原 prompt 不变重试一次；仍失败时报告错误摘要。

## API Key 处理

- 只从 `COMATE_API_KEY` 或 `COMATE_API_KEY_FILE` 读取密钥；不要把 key 写入仓库、prompt、README、版本记录、命令行参数或最终回复。
- 运行前需要判断 key 是否存在时，不要用会打印密钥的命令；只做存在性检查。
- 如果 key 缺失，或脚本返回 `auth_error` / HTTP 401 / HTTP 403，必须使用 `ask-user-question` 的结构化询问方式处理：
  - 推荐选项：`我先设置环境变量 (Recommended)`：用户在自己的 shell 设置 `COMATE_API_KEY` 后重试，最少暴露密钥。
  - 备选：`使用 key 文件`：用户提供只含密钥的本地文件路径，通过 `COMATE_API_KEY_FILE` 或 `--api-key-file` 读取。
  - 备选：`本轮临时提供`：仅在当前环境有安全传递方式时使用；不要复述、保存或提交密钥。
- 如果当前环境没有结构化询问工具，按 `ask-user-question` skill 的降级格式询问，不要继续猜测或伪造 key。

## Progressive Disclosure

- `references/comate-image-apis.md`：三条接口链路、默认模型、请求结构、返回 base64 路径和使用建议。
- `scripts/comate_image_client.py`：标准库 Comate 图片客户端和 CLI，支持自动扩展名、语义化输出名、key 文件读取和认证错误识别。
