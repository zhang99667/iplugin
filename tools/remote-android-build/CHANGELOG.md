# 变更日志

## 0.1.4

版本记录：`versions/v0.1.4.md`

### 变更

- `remote-build.zsh` 用 `REMOTE_COMMAND` 作为远端编译入口，在 `REMOTE_ROOT` 下执行。
- 默认命令是 `./gradlew :app:assembleDebug`。不再读取 `TASK` 或 `REMOTE_GRADLE_ARGS`。
- `init-project.zsh` 和示例配置默认写出 `REMOTE_COMMAND`，不再生成 `TASK`。
- `--print-config` 和 README 同步改成单命令入口。

### 设计取舍

- 远端只执行一条命令。Gradle task 和额外参数都写进 `REMOTE_COMMAND`。
- 执行目录固定为 `REMOTE_ROOT`，不再另加 cwd 配置。
- 不在脚本里解析 `run64` 或加载远端 alias；自定义命令由远端非交互 shell 直接执行。

## 0.1.3

版本记录：`versions/v0.1.3.md`

### 变更

- `remote-build.zsh` 新增 `SYNC_GIT_METADATA`，默认同步 `.git/.mgit`，让远端分支、HEAD 和暂存区跟随本地。
- rsync 同步时默认用 include 规则覆盖旧 `.remote-buildignore` 中的 `.git/`、`.mgit/` 排除项，避免已有项目继续保留远端旧分支状态。
- `remote-buildignore.template` 不再默认排除 `.git/.mgit`；如需保留远端 clone，可在配置里设置 `SYNC_GIT_METADATA=0`。
- README、配置示例和实施文档同步说明 Git 元数据同步策略。

### 设计取舍

- 默认优先保证远端镜像与本地工作区一致，而不是减少 Git 对象传输量。
- 保留 `SYNC_GIT_METADATA=0` 兼容大仓库或特殊 worktree 场景。

## 0.1.2

版本记录：`versions/v0.1.2.md`

### 变更

- `init-project.zsh` 生成的 `.remote-build.zsh` 为每个核心配置项补充中文注释。
- `remote-build.env.example` 和 README 的配置示例同步补充逐项说明。

### 设计取舍

- 仍保持配置键名不变，只提升生成配置的自解释性。
- 不覆盖已经存在的项目配置文件，避免破坏用户手工修改过的远程构建参数。

## 0.1.1

版本记录：`versions/v0.1.1.md`

### 变更

- 将 `init-project.zsh` 的初始化提示、错误提示和生成配置注释改为中文。
- 将 `remote-build.zsh` 的帮助信息、阶段输出、错误提示和完成提示改为中文。
- 将 `remote-build.env.example` 的说明注释改为中文。

### 设计取舍

- 保留命令参数、环境变量和配置键名的英文形式，避免破坏现有脚本调用和项目配置。

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
