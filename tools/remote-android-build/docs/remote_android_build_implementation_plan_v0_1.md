# Android 远程构建工具实施方案 v0.1.0

> 版本记录：`../versions/v0.1.0.md`
>
> 状态：已实施。
>
> 原始探索方案：`./android_remote_build_workflow.html`

## 0. 背景材料

本实施方案来自本地 HTML 方案《Android 双 Mac 远程编译工作流实施方案》的收敛结果。HTML 文件保留了早期对 VNC、SSH、JetBrains Gateway、远端打包和本地 adb 安装等路径的完整讨论；本工具只落地其中已经验证可行、且适合沉淀为脚本的 SSH + rsync + 远端 Gradle + 本地 adb 闭环。

HTML 文件已归档到本目录：

```text
tools/remote-android-build/docs/android_remote_build_workflow.html
```

仓库内以 `docs/android_remote_build_workflow.html` 为准。

## 1. 目标与边界

### 1.1 本期目标

实现一个可复用的本地工具，用于 Android 双 Mac 远程构建：

1. 本地 Mac 仍作为唯一编辑入口和真机调试入口。
2. 远端 M4 Mac 作为本地工程的构建镜像。
3. 本地通过 SSH 和 rsync 同步源码到远端。
4. 远端执行 Gradle task 生成 APK。
5. 本地拉回 APK，并通过本地 adb 安装到手边真机。

### 1.2 明确不做

1. 不接入 Mutagen 实时同步。
2. 不配置 Gradle Remote Build Cache。
3. 不配置 Tailscale、VNC 或其他网络通道。
4. 不处理 split APK 的自动安装编排。
5. 不修改具体 Android 工程的 Gradle 配置。

## 2. 目标文件结构

```text
tools/remote-android-build/
  README.md
  CHANGELOG.md
  AGENTS.md
  CLAUDE.md
  init-project.zsh
  remote-build.zsh
  remote-build.env.example
  remote-buildignore.template
  docs/
    android_remote_build_workflow.html
    remote_android_build_implementation_plan_v0_1.md
  versions/
    README.md
    v0.1.0.md
```

## 3. 脚本职责

### 3.1 `init-project.zsh`

`init-project.zsh` 只做本地初始化：

- 校验目标目录存在。
- 校验目标目录包含 `gradlew`。
- 如果缺少 `.remote-buildignore`，复制默认模板。
- 如果缺少 `.remote-build.zsh`，生成项目级配置。
- 不连接远端，不执行 rsync，不执行 Gradle。

### 3.2 `remote-build.zsh`

`remote-build.zsh` 是主执行入口：

- 读取 `--config` 指定的项目配置，或自动读取当前目录的 `.remote-build.zsh`。
- 计算最终配置，并允许 `--dry-run`、`--no-install` 覆盖配置文件。
- 检查本地依赖：`ssh`、`rsync`，需要安装时再检查 `adb`。
- 创建远端镜像目录。
- 用 rsync 同步本地工程到远端镜像目录。
- 远端执行 `./gradlew $TASK $REMOTE_GRADLE_ARGS`。
- 查找最新 APK 并拉回本地。
- 可选执行本地 `adb install -r -d`。

## 4. 架构决策

- 使用 zsh 而不是 Python：目标流程主要是 SSH、rsync、Gradle 和 adb 编排，shell 更直接。
- 使用项目级 `.remote-build.zsh`：不同 Android 工程的模块、flavor、APK 输出路径差异较大，配置文件比命令行参数更可维护。
- 使用 `--delete-delay`：保持远端镜像与本地一致，同时降低同步中断造成半删除状态的概率。
- 默认排除 `.git` 和 `.mgit`：避免同步大量 Git 内部对象；需要 Git 元数据的项目应在远端保留 clone 或显式传入版本信息。
- 安装步骤可关闭：split APK、AAB 和只拉包验证的场景不应被单 APK 安装逻辑阻塞。

## 5. 风险与处理

| 风险 | 影响 | 处理 |
| --- | --- | --- |
| rsync 删除远端私有文件 | 签名、local.properties 或临时配置丢失 | secrets 放在 `REMOTE_ROOT` 外，首次运行 `DRY_RUN=1` |
| debug 签名不一致 | 覆盖安装失败 | 统一 debug keystore，或首次切换时卸载旧包 |
| 远端 Git 元数据滞后 | 版本号或 commit id 错误 | 远端 clone 保持基线一致，或通过 Gradle 参数传入 |
| APK 输出路径不匹配 | 构建成功但拉包失败 | 在 `.remote-build.zsh` 中修改 `APK_GLOB` |
| 多设备连接 | adb 不知道安装到哪台设备 | 使用 `ADB_SERIAL` 指定设备 |

## 6. 验证记录

- `zsh -n tools/remote-android-build/init-project.zsh`：通过。
- `zsh -n tools/remote-android-build/remote-build.zsh`：通过。
- `tools/remote-android-build/remote-build.zsh --help`：通过。
- 使用 `--print-config` 在 `baiduapp-android/client` 下验证配置解析：通过。
- `python3 scripts/validate-plugin.py`：10 项插件结构校验通过。
