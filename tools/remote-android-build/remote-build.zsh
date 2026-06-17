#!/usr/bin/env zsh
set -euo pipefail

# 脚本必须能从任意工作目录被调用，所以先记录自身目录，用来寻找
# 默认的 remote-buildignore.template。:A 是 zsh 的绝对路径修饰符。
SCRIPT_DIR="${0:A:h}"

# 命令行参数先暂存在 *_CLI 变量里。配置文件会在参数解析后 source，
# 所以最终需要让命令行参数覆盖配置文件中的同名设置。
CONFIG_FILE=""
DRY_RUN_CLI=""
INSTALL_APK_CLI=""
PRINT_CONFIG=0

# 只保留少量参数，避免把脚本做成复杂构建系统。项目差异通过
# .remote-build.zsh 配置文件表达，命令行只负责临时开关。
usage() {
  cat <<EOF
用法：
  remote-build.zsh [--config path] [--dry-run] [--no-install] [--print-config]

环境变量/配置项：
  REMOTE              远端 SSH host alias。默认：buildmac
  LOCAL_ROOT          本地 Android Gradle 工程根目录。默认：当前目录
  REMOTE_ROOT         远端镜像目录。默认：~/remote-work/<project>
  TASK                Gradle task。默认：:app:assembleDebug
  APK_GLOB            相对 REMOTE_ROOT 的 APK 匹配表达式。默认：app/build/outputs/apk/debug/*.apk
  LOCAL_APK_DIR       拉回 APK 后存放的本地目录。默认：~/Downloads/android-artifacts
  INSTALL_APK         构建后安装填 1，只拉回填 0。默认：1
  ADB_SERIAL          可选的本地 adb 设备 serial
  REMOTE_GRADLE_ARGS  可选的额外 Gradle 参数
  IGNORE_FILE         可选的 rsync 排除文件
EOF
}

# 参数解析只处理脚本自身的开关。Gradle 参数不要混在这里解析，
# 统一通过 REMOTE_GRADLE_ARGS 传给远端 ./gradlew，避免 shell quoting
# 规则在本地和远端之间变得不可预测。
while [[ $# -gt 0 ]]; do
  case "$1" in
    --config)
      CONFIG_FILE="${2:-}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN_CLI=1
      shift
      ;;
    --no-install)
      INSTALL_APK_CLI=0
      shift
      ;;
    --print-config)
      PRINT_CONFIG=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "未知参数：$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

# 如果用户在 Android 工程根目录里放了 .remote-build.zsh，允许直接运行
# remote-build.zsh 而不显式传 --config。这是日常使用的最短路径。
if [[ -z "$CONFIG_FILE" && -f "$PWD/.remote-build.zsh" ]]; then
  CONFIG_FILE="$PWD/.remote-build.zsh"
fi

# 配置文件是普通 zsh，允许项目按需设置 REMOTE、TASK、APK_GLOB 等变量。
# 这里主动检查文件存在，避免 source 一个空路径或拼错路径时静默退回默认值。
if [[ -n "$CONFIG_FILE" ]]; then
  if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "配置文件不存在：$CONFIG_FILE" >&2
    exit 1
  fi
  source "$CONFIG_FILE"
fi

# 统一计算最终配置。默认值只覆盖常见 Android 单 APK debug 构建场景；
# 复杂项目应该在 .remote-build.zsh 里显式设置 TASK 和 APK_GLOB。
REMOTE="${REMOTE:-buildmac}"
LOCAL_ROOT="${LOCAL_ROOT:-$PWD}"
LOCAL_ROOT="${LOCAL_ROOT:A}"
PROJECT_NAME="${LOCAL_ROOT:t}"
REMOTE_ROOT="${REMOTE_ROOT:-~/remote-work/$PROJECT_NAME}"
TASK="${TASK:-:app:assembleDebug}"
APK_GLOB="${APK_GLOB:-app/build/outputs/apk/debug/*.apk}"
LOCAL_APK_DIR="${LOCAL_APK_DIR:-$HOME/Downloads/android-artifacts}"
INSTALL_APK="${INSTALL_APK:-1}"
DRY_RUN="${DRY_RUN:-0}"

# 命令行开关优先级高于配置文件。这样即使项目配置 INSTALL_APK=1，
# 临时执行 --no-install 也能只构建和拉包，不会误装到当前连接的设备。
if [[ -n "$INSTALL_APK_CLI" ]]; then
  INSTALL_APK="$INSTALL_APK_CLI"
fi
if [[ -n "$DRY_RUN_CLI" ]]; then
  DRY_RUN="$DRY_RUN_CLI"
fi
REMOTE_GRADLE_ARGS="${REMOTE_GRADLE_ARGS:-}"

# 优先使用项目自己的 .remote-buildignore；如果项目还没初始化，则退回到
# 工具目录里的模板。这样可以直接 dry-run 一个未初始化项目，也能让项目
# 后续维护自己的排除规则。
IGNORE_FILE="${IGNORE_FILE:-$LOCAL_ROOT/.remote-buildignore}"
if [[ ! -f "$IGNORE_FILE" ]]; then
  IGNORE_FILE="$SCRIPT_DIR/remote-buildignore.template"
fi

# 依赖检查放在真正执行前，报错尽量早。adb 只有在需要安装 APK 时才检查，
# 允许用户在没有本地 Android 设备环境的机器上只做远程构建和拉包。
need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "缺少命令：$1" >&2
    exit 1
  fi
}

# 远端命令需要 cd/mkdir 到 REMOTE_ROOT。路径里可能包含空格，普通双引号
# 组合很容易在本地和远端两层 shell 之间出错。这里用 zsh ${(q)...}
# 转义路径，同时保留 ~/ 前缀，让远端 shell 展开成远端用户 HOME。
remote_path_expr() {
  local p="$1"
  if [[ "$p" == "~" ]]; then
    print -r -- "~"
  elif [[ "$p" == "~/"* ]]; then
    local rest="${p#~/}"
    print -r -- "~/${(q)rest}"
  else
    print -r -- "${(q)p}"
  fi
}

# --print-config 用于只读检查最终配置，不连接远端、不执行 rsync。
# 这能快速确认 CLI 参数覆盖、配置文件 source 和默认值是否符合预期。
print_config() {
  cat <<EOF
REMOTE=$REMOTE
LOCAL_ROOT=$LOCAL_ROOT
REMOTE_ROOT=$REMOTE_ROOT
TASK=$TASK
APK_GLOB=$APK_GLOB
LOCAL_APK_DIR=$LOCAL_APK_DIR
INSTALL_APK=$INSTALL_APK
ADB_SERIAL=${ADB_SERIAL:-}
REMOTE_GRADLE_ARGS=$REMOTE_GRADLE_ARGS
IGNORE_FILE=$IGNORE_FILE
DRY_RUN=$DRY_RUN
EOF
}

need_cmd ssh
need_cmd rsync
if [[ "$INSTALL_APK" == "1" ]]; then
  need_cmd adb
fi

# 这些本地前置条件可以在联网前验证。LOCAL_ROOT 必须是 Gradle 根目录，
# gradlew 必须可执行；否则即使同步到远端也无法按预期构建。
if [[ ! -d "$LOCAL_ROOT" ]]; then
  echo "LOCAL_ROOT 不存在：$LOCAL_ROOT" >&2
  exit 1
fi
if [[ ! -x "$LOCAL_ROOT/gradlew" ]]; then
  echo "gradlew 不存在或不可执行：$LOCAL_ROOT/gradlew" >&2
  exit 1
fi
if [[ ! -f "$IGNORE_FILE" ]]; then
  echo "排除规则文件不存在：$IGNORE_FILE" >&2
  exit 1
fi

if [[ "$PRINT_CONFIG" == "1" ]]; then
  print_config
  exit 0
fi

# 本地 APK 目录先创建，避免构建完成后才因为本地目录不存在失败。
mkdir -p "$LOCAL_APK_DIR"
remote_root_q="$(remote_path_expr "$REMOTE_ROOT")"

# 先在远端创建镜像目录。REMOTE_ROOT 应视为可丢弃工作镜像，持久的
# SDK、签名文件、local.properties 等机器私有配置不应该放在这个目录里。
echo "[1/5] 准备远端镜像目录"
ssh "$REMOTE" "mkdir -p $remote_root_q"

# 同步源码到远端。--delete-delay 会删除远端本地已经不存在的文件，
# 但延迟到传输结束后执行，降低中途失败导致远端处于半删除状态的概率。
# 首次使用前建议 DRY_RUN=1，确认排除规则不会删掉远端需要保留的文件。
echo "[2/5] 同步源码"
rsync_args=(-az --delete-delay --human-readable)
if command rsync --info=help >/dev/null 2>&1; then
  rsync_args+=(--info=stats1,progress2)
else
  rsync_args+=(--stats)
fi
if [[ "$DRY_RUN" == "1" ]]; then
  rsync_args+=(--dry-run)
fi
rsync "${rsync_args[@]}" \
  --exclude-from="$IGNORE_FILE" \
  "$LOCAL_ROOT/" "$REMOTE:$REMOTE_ROOT/"

if [[ "$DRY_RUN" == "1" ]]; then
  echo "DRY_RUN=1：同步预览已完成，未开始编译。"
  exit 0
fi

# 远端只负责构建，不负责安装手机。这样 Android Studio、Logcat 和真机
# 仍留在本地 Mac，避免远程桌面/VNC 快捷键和手势问题。
echo "[3/5] 远端编译"
ssh "$REMOTE" "cd $remote_root_q && ./gradlew $TASK $REMOTE_GRADLE_ARGS"

# 构建成功后在远端按修改时间找最新 APK。APK_GLOB 是相对 REMOTE_ROOT
# 的表达式，适用于常见 app/build/outputs/apk/... 单 APK 输出。
echo "[4/5] 拉回 APK"
remote_apk="$(
  ssh "$REMOTE" "cd $remote_root_q && ls -t $APK_GLOB 2>/dev/null | head -1"
)"
if [[ -z "$remote_apk" ]]; then
  echo "远端没有匹配到 APK：$APK_GLOB" >&2
  exit 1
fi

# 支持 APK_GLOB 返回相对路径、绝对路径或 ~/ 开头路径。常规场景下
# ls 返回相对路径，此时需要拼回 REMOTE_ROOT 再用 rsync 拉取。
if [[ "$remote_apk" == /* || "$remote_apk" == "~/"* ]]; then
  remote_src="$remote_apk"
else
  remote_src="$REMOTE_ROOT/$remote_apk"
fi
rsync -P "$REMOTE:$remote_src" "$LOCAL_APK_DIR/"
local_apk="$LOCAL_APK_DIR/${remote_apk:t}"
echo "已拉回：$local_apk"

# 安装是可选步骤。split APK、AAB 或只想交给别人验证的场景，可以通过
# INSTALL_APK=0 或 --no-install 跳过安装，只保留构建产物。
if [[ "$INSTALL_APK" != "1" ]]; then
  echo "[5/5] 已跳过安装"
  exit 0
fi

echo "[5/5] 安装 APK"
adb_target=()

# 多设备连接时必须指定 ADB_SERIAL，否则 adb install 会因为设备不唯一失败。
# 这里不自动选择设备，避免把包装到错误的手机上。
if [[ -n "${ADB_SERIAL:-}" ]]; then
  adb_target=(-s "$ADB_SERIAL")
fi

# -r 允许覆盖安装，-d 允许 debug 场景版本号回退。签名不一致仍会失败，
# 这种情况应统一 debug keystore，或首次切换时手动卸载旧包。
if ! adb "${adb_target[@]}" install -r -d "$local_apk"; then
  echo "adb install 失败。" >&2
  echo "如果错误是 INSTALL_FAILED_UPDATE_INCOMPATIBLE，请统一两台 Mac 的 debug keystore，或先卸载旧包再安装一次。" >&2
  exit 1
fi

echo "完成。"
