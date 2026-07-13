#!/usr/bin/env python3
"""回归测试 Obsidian 笔记校验器的发布契约和结构边界。"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


VALIDATOR = Path(__file__).resolve().parents[1] / "scripts" / "validate_note.py"


class ValidateNoteTest(unittest.TestCase):
    def run_validator(
        self,
        content: str,
        *,
        strict: bool = True,
        assets: dict[str, str | bytes] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        # 每个 case 使用独立临时目录，避免测试之间共享笔记状态。
        with tempfile.TemporaryDirectory() as directory:
            note = Path(directory) / "note.md"
            note.write_text(content, encoding="utf-8")
            for relative_path, asset_content in (assets or {}).items():
                # 测试资产按笔记相对路径创建，覆盖真实 Vault 的附件解析方式。
                asset = note.parent / relative_path
                asset.parent.mkdir(parents=True, exist_ok=True)
                if isinstance(asset_content, bytes):
                    asset.write_bytes(asset_content)
                else:
                    asset.write_text(asset_content, encoding="utf-8")
            command = ["python3", str(VALIDATOR)]
            if strict:
                command.append("--strict")
            command.append(str(note))
            return subprocess.run(command, text=True, capture_output=True, check=False)

    def test_valid_post_passes(self) -> None:
        result = self.run_validator(
            """---
publish: true
type: post
title: Agent Skills 完全指南
date: 2026-07-09
summary: 说明 Agent Skills 的设计和使用边界。
tags: [AI, Agent, Engineering]
---
## 核心结论
正文。

---
## 相关笔记
"""
        )
        self.assertEqual(0, result.returncode, result.stderr)

    def test_valid_private_note_passes(self) -> None:
        result = self.run_validator(
            """---
publish: false
type: note
topic: AI
---
## 核心结论
正文。

---
## 相关笔记
"""
        )
        self.assertEqual(0, result.returncode, result.stderr)

    def test_note_requires_topic(self) -> None:
        result = self.run_validator(
            """---
publish: false
type: note
---
## 结论
正文。

---
## 相关笔记
"""
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("topic", result.stderr)

    def test_post_rejects_invalid_calendar_date(self) -> None:
        result = self.run_validator(
            """---
publish: true
type: post
title: 标题
date: 2026-02-30
summary: 有效摘要。
tags: [AI]
---
## 正文
内容。

---
## 相关笔记
"""
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("有效日历日期", result.stderr)

    def test_h1_is_rejected(self) -> None:
        result = self.run_validator(
            """---
publish: false
type: note
topic: AI
---
# 重复标题
正文。

---
## 相关笔记
"""
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("一级标题", result.stderr)

    def test_strict_mode_requires_related_notes(self) -> None:
        result = self.run_validator(
            """---
publish: false
type: note
topic: AI
---
## 正文
内容。
"""
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("相关笔记", result.stderr)

    def test_existing_obsidian_svg_embed_passes(self) -> None:
        result = self.run_validator(
            """---
publish: false
type: note
topic: AI
---
## 运行机制
![[img/runtime.svg|760]]

---
## 相关笔记
""",
            assets={"img/runtime.svg": '<svg xmlns="http://www.w3.org/2000/svg"></svg>'},
        )
        self.assertEqual(0, result.returncode, result.stderr)

    def test_missing_obsidian_image_is_rejected(self) -> None:
        result = self.run_validator(
            """---
publish: false
type: note
topic: AI
---
## 运行机制
![[img/missing.png|760]]

---
## 相关笔记
"""
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("本地图片不存在", result.stderr)

    def test_markdown_image_and_remote_image_are_distinguished(self) -> None:
        result = self.run_validator(
            """---
publish: false
type: note
topic: AI
---
## 运行机制
![本地图](img/runtime.png)
![远程图](https://example.com/runtime.png)

---
## 相关笔记
""",
            assets={"img/runtime.png": b"not-decoded-by-structure-validator"},
        )
        self.assertEqual(0, result.returncode, result.stderr)

    def test_image_example_in_fenced_code_is_ignored(self) -> None:
        result = self.run_validator(
            """---
publish: false
type: note
topic: AI
---
## 图片语法
```markdown
![[img/example.svg|760]]
```

---
## 相关笔记
"""
        )
        self.assertEqual(0, result.returncode, result.stderr)

    def test_malformed_svg_is_rejected(self) -> None:
        result = self.run_validator(
            """---
publish: false
type: note
topic: AI
---
## 运行机制
![[img/broken.svg|760]]

---
## 相关笔记
""",
            assets={"img/broken.svg": "<svg><text>broken</svg>"},
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("SVG 无法解析", result.stderr)

    def test_non_svg_xml_with_svg_suffix_is_rejected(self) -> None:
        result = self.run_validator(
            """---
publish: false
type: note
topic: AI
---
## 运行机制
![[img/not-svg.svg|760]]

---
## 相关笔记
""",
            assets={"img/not-svg.svg": "<document><text>not svg</text></document>"},
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("根元素不是 svg", result.stderr)

    def test_mixed_fence_does_not_hide_later_structure_or_images(self) -> None:
        result = self.run_validator(
            """---
publish: false
type: note
topic: AI
---
## 图片语法
```markdown
~~~
```
   # 重复标题
![[img/missing.png]]

---
## 相关笔记
"""
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("一级标题", result.stderr)
        self.assertIn("本地图片不存在", result.stderr)

    def test_invalid_flow_style_frontmatter_is_rejected(self) -> None:
        result = self.run_validator(
            """---
publish: true
type: post
title: [unterminated
date: 2026-07-13
summary: 有效摘要。
tags: [AI]
---
## 正文
内容。

---
## 相关笔记
"""
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("flow value 未闭合", result.stderr)

    def test_unquoted_colon_scalar_is_rejected(self) -> None:
        result = self.run_validator(
            """---
publish: true
type: post
title: foo: bar
date: 2026-07-13
summary: 有效摘要。
tags: [AI]
---
## 正文
内容。

---
## 相关笔记
"""
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("含冒号的标量必须加引号", result.stderr)

    def test_related_notes_requires_separator_and_last_heading_position(self) -> None:
        result = self.run_validator(
            """---
publish: false
type: note
topic: AI
---
## 正文
内容。
## 相关笔记
## 后续正文
不应出现在相关笔记之后。
"""
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("前必须使用 --- 分隔", result.stderr)
        self.assertIn("必须是最后一个标题", result.stderr)

    def test_inline_code_image_example_is_ignored(self) -> None:
        result = self.run_validator(
            """---
publish: false
type: note
topic: AI
---
## 图片语法
行内示例 `![[img/missing.svg|760]]` 不是真实附件。

---
## 相关笔记
"""
        )
        self.assertEqual(0, result.returncode, result.stderr)

    def test_indented_h1_is_rejected(self) -> None:
        result = self.run_validator(
            """---
publish: false
type: note
topic: AI
---
## 正文
内容。
   # 重复标题

---
## 相关笔记
"""
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("一级标题", result.stderr)

    def test_setext_h1_is_rejected(self) -> None:
        result = self.run_validator(
            """---
publish: false
type: note
topic: AI
---
## 正文
重复标题
===

---
## 相关笔记
"""
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("Setext 一级标题", result.stderr)


if __name__ == "__main__":
    unittest.main()
