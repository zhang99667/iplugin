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
  echo "项目根目录不存在：$PROJECT_ROOT" >&2
  exit 1
fi

# 这个工具只面向 Android Gradle 工程根目录。用 gradlew 做轻量判断，
# 可以避免用户在 workspace 根目录、子模块目录或普通源码目录误初始化。
if [[ ! -f "$PROJECT_ROOT/gradlew" ]]; then
  echo "项目根目录下没有找到 gradlew：$PROJECT_ROOT" >&2
  echo "请在 Android Gradle 工程根目录运行，例如 baiduapp-android/client。" >&2
  exit 1
fi

# .remote-buildignore 控制 rsync 排除规则，.remote-build.zsh 控制某个项目
# 的远端主机、远端目录、编译命令和 APK 输出路径。两个文件都放在
# 项目根目录，方便每个 Android 工程独立维护自己的远程构建参数。
IGNORE_FILE="$PROJECT_ROOT/.remote-buildignore"
CONFIG_FILE="$PROJECT_ROOT/.remote-build.zsh"

# 如果项目已经有自己的 ignore/config，保持不覆盖。远程构建配置往往会
# 包含项目特有的模块名、flavor、签名路径约定，覆盖会破坏已有调试环境。
if [[ ! -f "$IGNORE_FILE" ]]; then
  cp "$SCRIPT_DIR/remote-buildignore.template" "$IGNORE_FILE"
  echo "已创建 $IGNORE_FILE"
else
  echo "已保留现有 $IGNORE_FILE"
fi

# 生成的是一份可读、可直接编辑的 zsh 配置。默认值只覆盖常见
# :app:assembleDebug 单 APK 场景；复杂 flavor、split APK 或 AAB 项目
# 需要用户按项目实际输出修改 REMOTE_COMMAND 和 APK_GLOB。
if [[ ! -f "$CONFIG_FILE" ]]; then
  cat > "$CONFIG_FILE" <<EOF
# 远端 Mac 的 SSH alias，需要先在 ~/.ssh/config 中配置好。
REMOTE="buildmac"

# 本地 Android Gradle 工程根目录，也就是包含 gradlew 的目录。
LOCAL_ROOT="$PROJECT_ROOT"

# 远端用于接收 rsync 同步源码的镜像目录。这个目录会被 --delete-delay 清理，
# 不要把签名文件、local.properties 或其他远端私有配置放在这里。
REMOTE_ROOT="~/remote-work/$PROJECT_NAME"

# 是否同步 .git/.mgit 元数据。1 表示远端分支、HEAD 和暂存区跟随本地；
# 如果你明确要保留远端自己的 clone 元数据，可改成 0。
SYNC_GIT_METADATA="1"

# 远端编译命令，在上面的 REMOTE_ROOT 下执行。多 flavor 或包装脚本
# 直接改这一行；SSH 非交互会话通常不加载 alias。
REMOTE_COMMAND="./gradlew :app:assembleDebug"

# 相对 REMOTE_ROOT 的 APK 匹配路径。构建成功后脚本会取最新匹配到的 APK 拉回本地。
APK_GLOB="app/build/outputs/apk/debug/*.apk"

# APK 拉回本地后的保存目录。
LOCAL_APK_DIR="\$HOME/Downloads/android-artifacts"

# 是否在拉回 APK 后安装到本地连接的 Android 设备。1 表示安装，0 表示只拉回。
INSTALL_APK="1"

# 本地连接多台 Android 设备时使用。
# ADB_SERIAL="device-serial"
EOF
  echo "已创建 $CONFIG_FILE"
else
  echo "已保留现有 $CONFIG_FILE"
fi

# 最后只打印下一步命令，不自动连接远端。初始化阶段应该是纯本地操作，
# 真正同步前让用户先用 DRY_RUN=1 看清楚 rsync 会传什么、删什么。
echo
echo "下一步："
echo "  1. 如果模块名、远端编译命令或 APK 路径不同，编辑 $CONFIG_FILE。"
echo "  2. 先预览同步内容："
echo "     DRY_RUN=1 $SCRIPT_DIR/remote-build.zsh --config $CONFIG_FILE"
echo "  3. 构建并安装："
echo "     $SCRIPT_DIR/remote-build.zsh --config $CONFIG_FILE"
