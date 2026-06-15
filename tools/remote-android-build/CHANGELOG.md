# 变更日志

## 0.1.0

版本记录：`versions/v0.1.0.md`

### 新增

- 新增 `remote-build.zsh`，支持 SSH 创建远端镜像目录、rsync 增量同步、远端 Gradle 构建、APK 拉回和本地 adb 安装。
- 新增 `init-project.zsh`，可在 Android Gradle 工程根目录生成 `.remote-buildignore` 和 `.remote-build.zsh`。
- 新增 `remote-buildignore.template`，默认排除 `.git`、`.mgit`、`.gradle`、`build`、IDE 文件、签名文件和本地产物。
- 新增 `remote-build.env.example`，提供项目级配置示例。
- 新增 `docs/android_remote_build_workflow.html`，归档原始 HTML 探索方案。
- 新增中文 README、工具级维护指南、实施文档和版本记录。

### 设计取舍

- 初版只做 P0 闭环，不默认引入 Mutagen、Gradle Remote Cache、Tailscale 或 VNC。
- 远端目录被视为可丢弃镜像，机器私有配置必须放在镜像目录外。
- 复杂项目差异通过 `.remote-build.zsh` 配置表达，不在主脚本中硬编码业务工程。
