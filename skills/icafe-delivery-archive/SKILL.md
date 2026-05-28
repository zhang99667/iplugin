---
name: icafe-delivery-archive
version: 0.1.1
tags: [icafe, delivery, archive, documentation, requirement, summary]
description: iCafe 需求交付材料归档助手。当用户要求“根据这个详设/HTML/文档推断是哪个卡片”“整理到需求交付文件夹”“把需求描述和技术详设放一起”“归档 iCafe 卡片材料”“方便以后整理需求交付”时触发。该技能会从文件内容或文件名识别 iCafe 卡片号，查询卡片详情，创建桌面需求交付子目录，把 iCafe 需求描述与技术详设统一命名保存，并检查是否已有总结；没有总结时调用 project-summary 生成总结文档。
user_invocable: true
---

# iCafe 需求交付材料归档

## 目标

把一次需求的关键交付材料整理到统一目录，方便后续复盘、汇总和查找。

默认产物：

```text
~/Desktop/需求交付/<space>-<sequence> <需求名>/
├── 需求描述 · <space>-<sequence>.html
├── 技术详设 · <space>-<sequence>.html
└── 总结 · <space>-<sequence>.md（若目录里还没有总结）
```

## 触发场景

用户通常会给出一个本地详设文件、HTML 文件、卡片链接或卡片号，并要求整理：

- “根据这个内容，推断是哪个卡片，然后在桌面需求交付文件夹内创建对应的文件夹”
- “把需求描述和技术详设放进去”
- “帮我归档这个需求交付材料”
- “这个详设对应哪个 iCafe 卡片，整理到需求交付”
- “方便以后整理需求/交付/复盘”

如果用户只是查询卡片、创建卡片、改评论，应使用 iCafe 卡片助手；如果用户要写项目复盘总结，应使用 project-summary。

## 必要依赖

本技能需要使用 iCafe 客户端：

```python
sys.path.insert(0, '/Users/markz/.claude/skills/icafe-card-assistant')
from scripts.icafe_client import ICafeClient
```

认证 token 由 iCafe 客户端自动读取：

1. 环境变量 `COMATE_AUTH_TOKEN`
2. `~/.comate/login`

## 工作流

### 1. 读取输入材料并识别卡片

优先从以下位置识别卡片：

1. 文件名或 HTML `<title>` 中的 `<space>-<sequence>`，例如 `FEEDADS-23545`
2. 正文中的卡片链接：`/icafe/issue/{space}-{sequence}/show`
3. 正文中的显式卡片号，如 `FEEDADS-23545`
4. 如果无法识别，询问用户提供 space_id 和 sequence

读取本地文件时使用 Read 工具；如果内容很大，只需读取前 2000 行通常足够，因为标题、头部 meta、引用来源里一般会包含卡片号。

### 2. 查询 iCafe 卡片详情

识别到 `space_id` 和 `sequence` 后，调用：

```python
client = ICafeClient()
card = client.get_card_by_id(
    space_id=space_id,
    sequence=sequence,
    show_associations=True,
    show_children=True,
    show_okr=True,
    show_accumulate=True,
)
```

如果接口返回 `cards` 列表，取第一张；如果返回单卡对象，直接使用。

需要提取：

- `title`
- `detail`（iCafe 需求描述正文，通常是 HTML 转义字符串）
- `status`
- `createdTime`
- `lastModifiedTime`
- `createdUser.name` / `createdUser.username`
- `parent.title`（如有）

### 3. 创建交付目录

默认目录根为：

```text
/Users/markz/Desktop/需求交付
```

子目录命名：

```text
<space_id>-<sequence> <短需求名>
```

短需求名从卡片标题生成：

- 去掉开头重复日期、平台标签、需求类型标签，例如 `【Android】`、`【2026.05.11】`、`【产品需求】`
- 保留核心业务名，例如 `私信欢迎语二期（支持微信名片，表单交互优化）`
- 如果清洗后为空，使用原标题
- 移除 `/ : * ? " < > |` 等不适合文件名的字符

如果目录已存在，不要删除；直接覆盖同名的两份归档文件即可。不要移动或删除用户原始详设文件，默认复制一份。

### 4. 写入需求描述

生成：

```text
需求描述 · <space_id>-<sequence>.html
```

内容要求：

- 使用独立 HTML，包含 UTF-8、移动端 viewport、简洁样式
- 顶部展示卡片号、标题、状态、创建人、创建/更新时间、父卡片、iCafe 链接
- 主体使用 iCafe `detail` 正文；如果 detail 是 HTML 转义字符串，先 `html.unescape`
- 保留 iCafe 正文中的图片和链接

建议模板：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>需求描述 · SPACE-SEQUENCE</title>
  <style>
    body { margin:0; background:#f6f8fb; color:#1f2937; font:14px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }
    main { max-width:960px; margin:0 auto; padding:32px 24px 72px; }
    .header { background:linear-gradient(135deg,#1e3a8a,#2563eb); color:white; border-radius:16px; padding:24px 28px; margin-bottom:24px; }
    h1 { margin:0 0 10px; font-size:22px; line-height:1.35; }
    .meta { display:flex; flex-wrap:wrap; gap:12px; opacity:.92; font-size:13px; }
    .card { background:white; border:1px solid #e5e7eb; border-radius:14px; padding:22px 26px; box-shadow:0 4px 18px rgba(15,23,42,.06); }
    img { max-width:100%; height:auto; border-radius:8px; border:1px solid #e5e7eb; }
    a { color:#2563eb; }
  </style>
</head>
<body>
<main>
  <section class="header">...</section>
  <section class="card">ICAFE_DETAIL_HTML</section>
</main>
</body>
</html>
```

### 5. 写入技术详设

如果用户提供的是本地详设文件：

- 复制到目标目录
- 命名为：`技术详设 · <space_id>-<sequence>.<原扩展名>`
- 如果原文件不是 HTML，也保留原扩展名，例如 `.md`、`.docx`、`.pdf`

如果用户没有提供详设文件，只提供卡片号：

- 只生成需求描述
- 明确告诉用户“未提供技术详设文件，因此只生成了需求描述”

### 6. 检查并生成总结文档

每次整理目标文件夹时，都要检查目录内是否已有总结文档。总结文档用于以后快速回看这个需求的背景、交付内容、关键难点、结果收益和后续事项。

判断“已有总结”的规则：

- 目标目录下存在文件名包含 `总结`、`复盘`、`summary`、`retrospective` 任一关键词的 `.md`、`.html`、`.docx` 文件，即认为已有总结
- 如果已有总结，不要覆盖，也不要重复生成；只在最终输出里说明“已存在总结文档”
- 如果没有总结，调用 `project-summary` skill，根据 iCafe 需求描述、技术详设摘要和卡片元信息生成总结

生成总结时的推荐输入素材：

- 卡片标题、卡片号、状态、创建/更新时间、父卡片
- iCafe `detail` 中的项目背景、目标价值、需求详情
- 技术详设中的整体方案、改动文件、关键难点、待确认项/遗留项

总结文件命名：

```text
总结 · <space_id>-<sequence>.md
```

总结内容保持朴素、简洁，不写晋升口吻。默认结构：

```markdown
# <需求名>

**卡片：** <space_id>-<sequence>  
**状态：** <status>  
**链接：** <iCafe URL>

## 背景与目标
...

## 完成内容
...

## 关键难点
...

## 结果与收益
...

## 后续事项
...
```

如果调用 `project-summary` 后得到的是对话文本，需要把结果写入上述文件；不要只显示在对话里。

### 7. 输出给用户

完成后用简短结果说明：

```markdown
已归档到：`/Users/markz/Desktop/需求交付/FEEDADS-23545 私信欢迎语二期（支持微信名片，表单交互优化）`

包含：
- `需求描述 · FEEDADS-23545.html`
- `技术详设 · FEEDADS-23545.html`
- `总结 · FEEDADS-23545.md`
```

如果总结已存在，输出：

```markdown
总结文档已存在，未重复生成。
```

不要输出大段卡片正文、HTML 内容或总结全文。

## 推荐脚本片段

可直接用 Bash 运行 Python 完成查询和写文件。注意根据用户输入替换 `source_design`，并从文件内容自动提取卡片号。

```python
import json, html, shutil, re
from pathlib import Path
import sys
sys.path.insert(0, '/Users/markz/.claude/skills/icafe-card-assistant')
from scripts.icafe_client import ICafeClient

source_design = Path('/path/to/design.html')
text = source_design.read_text(encoding='utf-8', errors='ignore')
match = re.search(r'([A-Za-z][A-Za-z0-9_-]*)-(\d{2,})', source_design.name + '\n' + text[:20000])
if not match:
    raise SystemExit('未识别到 iCafe 卡片号，请让用户提供 space_id 和 sequence')
space_id, sequence = match.group(1), match.group(2)

client = ICafeClient()
resp = client.get_card_by_id(space_id=space_id, sequence=sequence, show_associations=True, show_children=True, show_okr=True, show_accumulate=True)
card = (resp.get('cards') or [resp])[0]

def safe_name(s):
    s = re.sub(r'【(?:Android|iOS|android|产品需求|技术需求|测试需求|\d{4}\.\d{2}\.\d{2}|\d{4}-\d{2}-\d{2})】', '', s)
    s = re.sub(r'[\\/:*?"<>|]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s or '未命名需求'

title = card.get('title') or f'{space_id}-{sequence}'
out_dir = Path('/Users/markz/Desktop/需求交付') / f'{space_id}-{sequence} {safe_name(title)}'
out_dir.mkdir(parents=True, exist_ok=True)

url = f'https://console.cloud.baidu-int.com/devops/icafe/issue/{space_id}-{sequence}/show'
detail = html.unescape(card.get('detail') or '')
created_user = card.get('createdUser') or {}
parent = card.get('parent') or {}

requirement_html = f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>需求描述 · {space_id}-{sequence}</title>
<style>body{{margin:0;background:#f6f8fb;color:#1f2937;font:14px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}}main{{max-width:960px;margin:0 auto;padding:32px 24px 72px}}.header{{background:linear-gradient(135deg,#1e3a8a,#2563eb);color:white;border-radius:16px;padding:24px 28px;margin-bottom:24px}}h1{{margin:0 0 10px;font-size:22px;line-height:1.35}}.meta{{display:flex;flex-wrap:wrap;gap:12px;opacity:.92;font-size:13px}}.card{{background:white;border:1px solid #e5e7eb;border-radius:14px;padding:22px 26px;box-shadow:0 4px 18px rgba(15,23,42,.06)}}img{{max-width:100%;height:auto;border-radius:8px;border:1px solid #e5e7eb}}a{{color:#2563eb}}</style>
</head><body><main><section class="header"><h1>需求描述 · {html.escape(title)}</h1><div class="meta"><span>卡片：{space_id}-{sequence}</span><span>状态：{html.escape(str(card.get('status') or ''))}</span><span>创建人：{html.escape(str(created_user.get('name') or created_user.get('username') or ''))}</span><span>创建：{html.escape(str(card.get('createdTime') or ''))}</span><span>更新：{html.escape(str(card.get('lastModifiedTime') or ''))}</span></div><div class="meta" style="margin-top:10px"><span>父卡片：{html.escape(str(parent.get('title') or '无'))}</span><span><a style="color:white;text-decoration:underline" href="{url}">打开 iCafe 卡片</a></span></div></section><section class="card">{detail}</section></main></body></html>'''

(out_dir / f'需求描述 · {space_id}-{sequence}.html').write_text(requirement_html, encoding='utf-8')
shutil.copy2(source_design, out_dir / f'技术详设 · {space_id}-{sequence}{source_design.suffix}')

summary_exists = any(
    p.is_file()
    and p.suffix.lower() in {'.md', '.html', '.docx'}
    and any(k in p.name.lower() for k in ['总结', '复盘', 'summary', 'retrospective'])
    for p in out_dir.iterdir()
)
if not summary_exists:
    print('NO_SUMMARY:', out_dir / f'总结 · {space_id}-{sequence}.md')
print(out_dir)
```

脚本只负责检测总结是否缺失；如果输出 `NO_SUMMARY:`，后续应调用 `project-summary` skill 生成总结内容，并写入该路径。

## 注意事项

- 不要猜默认空间 ID 或用户 ID；识别不到卡片号时询问用户。
- 不要把技术详设从原目录移动走，复制即可，避免破坏用户已有整理。
- 不要删除或清空已有需求交付目录。
- 不要生成 Markdown 需求描述，优先 HTML，因为 iCafe 正文通常含图片和富文本。
- 总结文档可以是 Markdown；它是二次提炼内容，不替代原始需求描述。
- 如果目标目录没有总结，要调用 `project-summary`，不要临场写一版风格不一致的总结。
- 如果 iCafe 接口返回过大，把完整 JSON 保存到工具结果即可，再用脚本提取字段生成文件。
