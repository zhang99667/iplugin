# Technical Solution Brief

目标：把 HTML 报告的代码高亮语言清单收敛为单一真源，避免新增语言时脚本、校验器和文档各维护一份清单。

当前问题：

- `highlight_code.py` 支持 Objective-C 后，`check_html_report.py` 仍保留旧白名单，导致合法输出被误报。
- `content-rules.md` 和 `visual-rules.md` 中也有语言列表，后续新增 Swift、C++、Go 时容易遗漏。

方案约束：

- 不引入第三方依赖。
- 校验脚本必须只读。
- 报告生成时仍保持单文件离线 HTML。

拟定方案：

- 在 `highlight_code.py` 增加 `--list-langs`，输出 JSON：`languages`、`aliases`、`text_like_languages`。
- `check_html_report.py` 通过 import 高亮脚本读取 `SUPPORTED_LANGS`。
- reference 文档不再写完整语言清单，改为要求使用 `--list-langs` 查询。

需要覆盖的验证：

- `python3 skills/html-report/scripts/highlight_code.py --list-langs` 输出合法 JSON。
- `python3 scripts/validate-plugin.py` 通过。
- 包含 Objective-C 代码块的 HTML 报告能通过 `check_html_report.py`。
