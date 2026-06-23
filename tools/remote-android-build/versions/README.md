# remote-android-build 版本索引

这个目录记录 `remote-android-build` 每次迭代的目标、变更、关联技术文档和交付范围。

| 版本 | 版本记录 | 关联技术文档 | 说明 |
| --- | --- | --- | --- |
| v0.1.3 | `v0.1.3.md` | `../docs/remote_android_build_implementation_plan_v0_1.md` | 默认同步 Git 元数据，修正远端分支和 HEAD 滞后问题。 |
| v0.1.2 | `v0.1.2.md` | 无新增技术文档 | 生成配置补充逐项中文注释。 |
| v0.1.1 | `v0.1.1.md` | 无新增技术文档 | 输出文案中文化，保留 shell 接口兼容。 |
| v0.1.0 | `v0.1.0.md` | `../docs/remote_android_build_implementation_plan_v0_1.md`、`../docs/android_remote_build_workflow.html` | SSH + rsync + 远端 Gradle + 本地 adb 的首个可运行版本。 |

## 维护规则

- 每次新增版本时，在本目录新增 `vX.Y.Z.md`。
- 版本记录必须写清楚目标、变更清单、架构决策、排除项和验证记录。
- 版本记录必须关联本版本使用的技术文档、实施方案和主要交付文件。
- 如果 `docs/` 中新增或改名技术文档，需要同步更新本索引和对应版本记录。
