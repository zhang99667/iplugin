# Android 远程构建工具

这个目录实现 Android 双 Mac 远程构建工作流的 P0 版本：

1. 在本地 Mac 写代码、看 Logcat、连接真机
2. 通过 SSH 和 rsync 把源码同步到远端 M4 Mac
3. 在远端 M4 Mac 上执行 Gradle 构建
4. 把最新 APK 拉回本地 Mac
5. 用本地 adb 安装到手边的 Android 设备

这个工具刻意只做最小闭环，不依赖 Mutagen、Gradle Remote Cache、Tailscale 或 VNC。
脚本提示、错误和生成配置中的说明默认使用中文；命令参数、环境变量和配置键名保持英文，以维持 shell 接口兼容。

## 快速开始

先确认本地有一个可用的 SSH alias，例如：

```sshconfig
Host buildmac
  HostName buildmac.local
  User your-user
  ServerAliveInterval 30
  ServerAliveCountMax 4
  ControlMaster auto
  ControlPath ~/.ssh/cm-%r@%h:%p
  ControlPersist 10m
```

进入 Android Gradle 工程根目录，初始化远程构建配置：

```bash
cd /path/to/android-project
/path/to/iplugin/tools/remote-android-build/init-project.zsh
```

如果你的模块名、Gradle task、远端目录或 APK 输出目录不同，编辑生成出来的 `.remote-build.zsh`。

首次运行建议先预览同步内容，不真正编译：

```bash
DRY_RUN=1 /path/to/iplugin/tools/remote-android-build/remote-build.zsh --config .remote-build.zsh
```

确认同步内容没问题后，执行构建、拉包和安装：

```bash
/path/to/iplugin/tools/remote-android-build/remote-build.zsh --config .remote-build.zsh
```

如果本地连接了多台设备，用 `ADB_SERIAL` 指定目标设备：

```bash
ADB_SERIAL=device-serial /path/to/iplugin/tools/remote-android-build/remote-build.zsh --config .remote-build.zsh
```

如果只想远程构建并拉回 APK，不安装到手机：

```bash
/path/to/iplugin/tools/remote-android-build/remote-build.zsh --config .remote-build.zsh --no-install
```

## 常用配置

`.remote-build.zsh` 是普通 zsh 配置文件：

```bash
# 远端 Mac 的 SSH alias，需要先在 ~/.ssh/config 中配置好。
REMOTE="buildmac"

# 本地 Android Gradle 工程根目录，也就是包含 gradlew 的目录。
LOCAL_ROOT="/path/to/android-project"

# 远端用于接收 rsync 同步源码的镜像目录。
REMOTE_ROOT="~/remote-work/client"

# 是否同步 .git/.mgit 元数据。
SYNC_GIT_METADATA="1"

# 远端执行的 Gradle task。
TASK=":app:assembleDebug"

# 相对 REMOTE_ROOT 的 APK 匹配路径。
APK_GLOB="app/build/outputs/apk/debug/*.apk"

# APK 拉回本地后的保存目录。
LOCAL_APK_DIR="$HOME/Downloads/android-artifacts"

# 是否在拉回 APK 后安装到本地连接的 Android 设备。
INSTALL_APK="1"
```

字段说明：

- `REMOTE`：远端 M4 Mac 的 SSH alias。
- `LOCAL_ROOT`：本地 Android Gradle 工程根目录。
- `REMOTE_ROOT`：远端镜像目录，脚本会用 rsync 同步到这里。
- `SYNC_GIT_METADATA`：`1` 表示同步 `.git/.mgit`，让远端分支、HEAD 和暂存区跟随本地；`0` 表示保留远端自己的 Git 元数据。
- `TASK`：远端执行的 Gradle task。
- `APK_GLOB`：相对 `REMOTE_ROOT` 的 APK 匹配表达式。
- `LOCAL_APK_DIR`：拉回 APK 后存放的本地目录。
- `INSTALL_APK`：`1` 表示拉回后安装，`0` 表示只拉回不安装。

如果项目输出 split APK，先设置 `INSTALL_APK=0`，把 APK 目录拉回后手动执行 `adb install-multiple`。等某个项目有稳定规则后，再在该项目配置里扩展专用安装逻辑。

## 注意事项

- 不要把 `local.properties`、keystore、证书和机器私有配置同步到远端镜像目录。
- 远端 `REMOTE_ROOT` 应该被视为可丢弃镜像；持久 SDK、签名文件和私有配置应放在镜像目录外。
- 默认会同步 `.git/.mgit` 元数据，即使旧项目的 `.remote-buildignore` 里仍写了 `.git/` 或 `.mgit/`；如果你明确要保留远端自己的 clone 元数据，把 `SYNC_GIT_METADATA` 设为 `0`。
- 如果 `adb install` 报 `INSTALL_FAILED_UPDATE_INCOMPATIBLE`，优先统一两台 Mac 的 debug keystore；不统一时只能首次切换时卸载旧包。
- 如果使用 Git worktree 或其他把 `.git` 指向外部目录的特殊布局，先用 `DRY_RUN=1` 确认同步内容；必要时把 `SYNC_GIT_METADATA` 设为 `0` 并通过 Gradle 参数显式传入版本信息。
- 首次使用 `--delete-delay` 前务必先跑 `DRY_RUN=1`，确认不会删除远端需要保留的文件。
