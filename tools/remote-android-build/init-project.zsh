#!/usr/bin/env zsh
set -euo pipefail

# 脚本位置用于定位同目录下的模板文件。使用 zsh 的 :A 修饰符转成
# 绝对路径，避免从其他目录调用脚本时找不到 remote-buildignore.template。
SCRIPT_DIR="${0:A:h}"

# 支持两种用法：
#   1. 在 Android Gradle 根目录直接运行 init-project.zsh
#   2. 传入一个项目根目录作为第一个参数
# PROJECT_ROOT 会被规范化为绝对路径，后续写入配置时不依赖当前目录。
PROJECT_ROOT="${1:-$PWD}"
PROJECT_ROOT="${PROJECT_ROOT:A}"
PROJECT_NAME="${PROJECT_ROOT:t}"

# 只接受存在的目录，避免把配置文件写到拼错的路径下面。
if [[ ! -d "$PROJECT_ROOT" ]]; then
  echo "Project root does not exist: $PROJECT_ROOT" >&2
  exit 1
fi

# 这个工具只面向 Android Gradle 工程根目录。用 gradlew 做轻量判断，
# 可以避免用户在 workspace 根目录、子模块目录或普通源码目录误初始化。
if [[ ! -f "$PROJECT_ROOT/gradlew" ]]; then
  echo "No gradlew found in project root: $PROJECT_ROOT" >&2
  echo "Run this from an Android Gradle root, for example baiduapp-android/client." >&2
  exit 1
fi

# .remote-buildignore 控制 rsync 排除规则，.remote-build.zsh 控制某个项目
# 的远端主机、远端目录、Gradle task 和 APK 输出路径。两个文件都放在
# 项目根目录，方便每个 Android 工程独立维护自己的远程构建参数。
IGNORE_FILE="$PROJECT_ROOT/.remote-buildignore"
CONFIG_FILE="$PROJECT_ROOT/.remote-build.zsh"

# 如果项目已经有自己的 ignore/config，保持不覆盖。远程构建配置往往会
# 包含项目特有的模块名、flavor、签名路径约定，覆盖会破坏已有调试环境。
if [[ ! -f "$IGNORE_FILE" ]]; then
  cp "$SCRIPT_DIR/remote-buildignore.template" "$IGNORE_FILE"
  echo "Created $IGNORE_FILE"
else
  echo "Kept existing $IGNORE_FILE"
fi

# 生成的是一份可读、可直接编辑的 zsh 配置。默认值只覆盖常见
# :app:assembleDebug 单 APK 场景；复杂 flavor、split APK 或 AAB 项目
# 需要用户按项目实际输出修改 TASK 和 APK_GLOB。
if [[ ! -f "$CONFIG_FILE" ]]; then
  cat > "$CONFIG_FILE" <<EOF
REMOTE="buildmac"
LOCAL_ROOT="$PROJECT_ROOT"
REMOTE_ROOT="~/remote-work/$PROJECT_NAME"

TASK=":app:assembleDebug"
APK_GLOB="app/build/outputs/apk/debug/*.apk"
LOCAL_APK_DIR="\$HOME/Downloads/android-artifacts"

INSTALL_APK="1"

# Use when multiple Android devices are attached locally.
# ADB_SERIAL="device-serial"

# Optional extra Gradle args.
# REMOTE_GRADLE_ARGS="-Pfoo=bar"
EOF
  echo "Created $CONFIG_FILE"
else
  echo "Kept existing $CONFIG_FILE"
fi

# 最后只打印下一步命令，不自动连接远端。初始化阶段应该是纯本地操作，
# 真正同步前让用户先用 DRY_RUN=1 看清楚 rsync 会传什么、删什么。
echo
echo "Next:"
echo "  1. Edit $CONFIG_FILE if module, task, or APK path is different."
echo "  2. Dry run:"
echo "     DRY_RUN=1 $SCRIPT_DIR/remote-build.zsh --config $CONFIG_FILE"
echo "  3. Build and install:"
echo "     $SCRIPT_DIR/remote-build.zsh --config $CONFIG_FILE"
