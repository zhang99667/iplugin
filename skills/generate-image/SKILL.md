---
name: generate-image
version: 0.1.5
description: 生成图片助手。当用户要求“生成图片”“出图”“画一张图”“根据 prompt 出图”“保存生成图片到本地”，或指定 gptimage、gpt-image-2、gptimg2、Responses image_generation、banana、banana2、Gemini、Comate 兼容图片接口时触发；泛泛出图可用平台内置能力，明确指定接口链路时必须走本地 API 客户端，默认并发生成 3 张候选图并视觉筛选只保留最佳图，自动为输出图片选择语义化文件名，路由词不会进入最终图片 prompt，并在 GENERATE_IMAGE_API_KEY 缺失或过期时使用 ask-user-question 询问用户提供或刷新密钥，首次提供后保存到本地私有缓存供后续复用。
tags: [generate-image, image, image-generation, api, gpt-image, banana, provider]
---

# 生成图片

目标：把图片生成做成通用流程。普通出图优先使用当前平台内置图像能力；用户明确指定 `gptimage`、`gpt-image-2`、`gptimg2`、`banana`、`banana2`、`responses`、Comate 等接口链路，或需要本地文件、可复现 CLI、私有网关时，必须使用内置 `generate_image_client.py` 客户端完成鉴权、接口选择、三候选并发生成、输出命名和最佳图留存。

## 触发边界

### 适用

- 用户要求“生成图片”“出图”“画一张图”“跑图片 API”“根据这个 prompt 出图”“保存生成图片到本地”。
- 用户提供图片生成 prompt，希望把输出保存为本地文件，并需要自动判断语义化文件名。
- 用户明确指定 `gptimage`、`gpt-image-2`、`gptimg2`、`Responses image_generation`、`banana`、`banana2`、Gemini 或 Comate 兼容图片接口。

### 不适用

- 用户只要求图片后处理、批量压缩、抠图或格式转换，且不需要重新生成图片。
- 用户要真实网页截图、Figma 设计或 SVG 技术图；分别使用浏览器/Figma/SVG 相关能力。

## 执行流程

1. 提炼 prompt。
   - 保留用户的主体、场景、风格、构图、比例、禁止文字/水印等要求。
   - 不擅自加入品牌、人名、敏感信息或用户未要求的元素。
   - 把 `generate-image`、`gptimg2`、`gpt-image-2`、`banana`、`banana2`、`responses`、`Comate`、`生成图片`、`出图`、`prompt 是` 等只用于触发或选路的词从最终图片 prompt 中剥离。
   - 例如用户说“用 banana2 生成图片：一只赛博风招财猫”，最终图片 prompt 应是“一只赛博风招财猫”，不是完整原话。
2. 选择执行方式。
   - 用户只是泛泛要求出图，且没有要求保存本地文件、指定接口链路、私有接口或比较链路时，优先使用当前平台内置图像生成能力。
   - 用户明确说 `gptimage`、`gptimg2`、`gpt-image-2`、`banana`、`banana2`、`responses`、Comate、Gemini，或要求保存本地文件、指定 API / backend / base URL、需要可复现 CLI 命令时，使用内置脚本；此时不要改走平台内置图像工具。
   - 需要接口细节时读取 `references/generate-image-apis.md`。
3. 选择脚本链路。
   - 默认使用 `images`，模型 `gpt-image-2`，结构最直接。
   - 用户说 `gptimage`、`gptimg2`、`gpt-image-2` 或没有指定模型时用 `images`。
   - 用户明确要 Responses 编排或工具链路时用 `responses`，模型 `gpt-5.5`。
   - 用户说 `banana`、`banana2` 或 Gemini 兼容链路时用 `banana`，模型 `gemini-3.1-flash-image-preview`。
   - 用户只是泛泛说“生成图片”时不要先问模型；只有用户要求选择、比较多链路，或明确问“用哪个模型”时才询问。
4. 判断输出名。
   - 不使用 `out.png`、`image.png`、`test.png` 这类泛名。
   - 根据 prompt 的主体、动作、场景或用途取 3 到 8 个语义词；中文 prompt 可用中文文件名，英文 prompt 用 kebab-case。
   - 只在对比多条链路时把 backend 或模型名放入文件名，例如 `programmer-noodles-images.png`。
   - 优先把语义名传给脚本的 `--stem`，让脚本自动补扩展名和避让重名文件。
5. 执行本地 API 生成。
   - 使用内置脚本：`skills/generate-image/scripts/generate_image_client.py`。
   - 默认并发生成 3 张候选图；只有用户明确要求“只出一张”或调试接口时才改为 `--candidates 1`。
   - 默认命令形态：

```bash
python3 skills/generate-image/scripts/generate_image_client.py images \
  --prompt "写实风格，一位程序员坐在电脑前吃泡面，不要文字和水印" \
  --stem "程序员夜晚泡面" \
  --candidates 3 \
  --out-dir ./outputs
```

6. 校验结果。
   - 命令输出必须包含每张候选图的 `candidate:`、`saved:`、`mime:`、`bytes:` 和 `response_path:`；单图模式没有 `candidate:`。
   - 打开或读取 3 张候选图，确认文件存在、大小非 0、格式正确。
   - 视觉比较候选图的主体完整度、构图、细节、文字/水印问题和 prompt 符合度；不要用字节大小、返回顺序等伪指标替代视觉判断。
   - 只保留最佳候选图：把最佳候选按语义化最终文件名留在 `outputs/`，删除另外两张候选图；如果需要向用户说明选择，简短说明保留哪一张以及原因。
   - 如果接口返回 502 或上游过载，原 prompt 不变重试一次；仍失败时报告错误摘要。

## API Key 处理

- 本地 API 客户端优先从 `GENERATE_IMAGE_API_KEY`、`GENERATE_IMAGE_API_KEY_FILE` 或默认缓存 `~/.config/iplugin/generate-image-api-key` 读取密钥；兼容读取旧的 `COMATE_API_KEY` / `COMATE_API_KEY_FILE`，但新流程不要再引导用户设置旧变量。
- 需要新密钥时，提示用户打开 `https://oneapi-comate.baidu-int.com/token`，复制自己的令牌。
- 给用户一个方便流程：打开 token 页面 -> 复制令牌 -> 选择下面任一方式提供给 agent -> agent 保存或读取密钥 -> agent 重试生成。
- 不要把 key 写入仓库、prompt、README、版本记录、命令行参数或最终回复。
- 如果用户选择直接粘贴令牌，优先通过脚本的 `--save-api-key-stdin` 从 stdin 保存到默认缓存或用户指定的 `--api-key-file`，文件权限由脚本设置为 `0600`；后续生成直接复用缓存，不再询问。
- 运行前需要判断 key 是否存在时，不要用会打印密钥的命令；只做存在性检查。
- 如果 key 缺失，或脚本返回 `auth_error` / HTTP 401 / HTTP 403，必须使用 `ask-user-question` 的结构化询问方式处理：
  - 推荐选项：`直接粘贴并保存 (Recommended)`：用户从 token 页面复制后直接发到聊天里，agent 通过 stdin 保存到本地私有缓存，不复述、不写命令行。
  - 备选：`使用 key 文件`：用户提供只含密钥的本地文件路径，通过 `GENERATE_IMAGE_API_KEY_FILE` 或 `--api-key-file` 读取。
  - 备选：`我先设置环境变量`：用户在自己的 shell 设置 `GENERATE_IMAGE_API_KEY` 后重试。
- 如果缓存 key 过期或返回 401 / 403，重新询问并用新的粘贴令牌覆盖缓存。
- 如果当前环境没有结构化询问工具，按 `ask-user-question` skill 的降级格式询问，不要继续猜测或伪造 key。

## Progressive Disclosure

- `references/generate-image-apis.md`：三条接口链路、默认模型、请求结构、返回 base64 路径和使用建议。
- `scripts/generate_image_client.py`：标准库图片生成客户端和 CLI，支持自动扩展名、语义化输出名、默认 key 缓存、stdin 保存和认证错误识别。
