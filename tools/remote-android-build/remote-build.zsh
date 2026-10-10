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
DELETE_EXCLUDED_CLI=""
PRUNE_BUILD_CLI=""
PRINT_CONFIG=0

# 只保留少量参数，避免把脚本做成复杂构建系统。项目差异通过
# .remote-build.zsh 配置文件表达，命令行只负责临时开关。
usage() {
  cat <<EOF
用法：
  remote-build.zsh [--config path] [--dry-run] [--no-install] [--prune-build MODE] [--delete-excluded] [--print-config]

环境变量/配置项：
  REMOTE              远端 SSH host alias。默认：buildmac
  LOCAL_ROOT          本地 Android Gradle 工程根目录。默认：当前目录
  REMOTE_ROOT         远端镜像目录。默认：~/remote-work/<project>
  REMOTE_COMMAND      远端编译命令，在 REMOTE_ROOT 下执行。默认：./gradlew :app:assembleDebug
  APK_GLOB            相对 REMOTE_ROOT 的 APK 匹配表达式。默认：app/build/outputs/apk/debug/*.apk
  LOCAL_APK_DIR       拉回 APK 后存放的本地目录。默认：~/Downloads/android-artifacts
  INSTALL_APK         构建后安装填 1，只拉回填 0。默认：1
  SYNC_GIT_METADATA   是否同步 .git/.mgit 元数据，保持远端分支和 HEAD 与本地一致。默认：1
  PRUNE_BUILD         远端中间产物清理策略：stale / all / off。默认：stale
  PRUNE_BUILD_NAMES   允许清理的中间产物目录名，空格分隔。默认：build
  DELETE_EXCLUDED     兼容旧配置。1 等价于 PRUNE_BUILD=all
  ADB_SERIAL          可选的本地 adb 设备 serial
  IGNORE_FILE         可选的 rsync 排除文件
EOF
}

# 参数解析只处理脚本自身的开关。远端编译参数写进 REMOTE_COMMAND，
# 不要混在这里解析，避免 shell quoting 规则在本地和远端之间变得不可预测。
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
    --prune-build)
      if [[ -z "${2:-}" || "${2}" == -* ]]; then
        echo "--prune-build 需要 stale、all 或 off" >&2
        usage >&2
        exit 2
      fi
      PRUNE_BUILD_CLI="$2"
      shift 2
      ;;
    --delete-excluded)
      DELETE_EXCLUDED_CLI=1
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

# 配置文件是普通 zsh，允许项目按需设置 REMOTE、REMOTE_COMMAND、APK_GLOB 等变量。
# 这里主动检查文件存在，避免 source 一个空路径或拼错路径时静默退回默认值。
if [[ -n "$CONFIG_FILE" ]]; then
  if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "配置文件不存在：$CONFIG_FILE" >&2
    exit 1
  fi
  source "$CONFIG_FILE"
fi

# 统一计算最终配置。默认值只覆盖常见 Android 单 APK debug 构建场景；
# 复杂项目应该在 .remote-build.zsh 里显式设置 REMOTE_COMMAND 和 APK_GLOB。
REMOTE="${REMOTE:-buildmac}"
LOCAL_ROOT="${LOCAL_ROOT:-$PWD}"
LOCAL_ROOT="${LOCAL_ROOT:A}"
PROJECT_NAME="${LOCAL_ROOT:t}"
REMOTE_ROOT="${REMOTE_ROOT:-~/remote-work/$PROJECT_NAME}"
APK_GLOB="${APK_GLOB:-app/build/outputs/apk/debug/*.apk}"
LOCAL_APK_DIR="${LOCAL_APK_DIR:-$HOME/Downloads/android-artifacts}"
INSTALL_APK="${INSTALL_APK:-1}"
DRY_RUN="${DRY_RUN:-0}"
SYNC_GIT_METADATA="${SYNC_GIT_METADATA:-1}"
PRUNE_BUILD="${PRUNE_BUILD:-}"
PRUNE_BUILD_NAMES="${PRUNE_BUILD_NAMES:-build}"
DELETE_EXCLUDED="${DELETE_EXCLUDED:-0}"
# 远端编译入口是完整命令，在 REMOTE_ROOT 下执行。未设置时退回常见
# assembleDebug，不再从 TASK / REMOTE_GRADLE_ARGS 拼装。
REMOTE_COMMAND="${REMOTE_COMMAND:-./gradlew :app:assembleDebug}"
REMOTE_COMMAND="${REMOTE_COMMAND#"${REMOTE_COMMAND%%[![:space:]]*}"}"
REMOTE_COMMAND="${REMOTE_COMMAND%"${REMOTE_COMMAND##*[![:space:]]}"}"
if [[ -z "$REMOTE_COMMAND" ]]; then
  echo "REMOTE_COMMAND 不能为空" >&2
  exit 1
fi

# 命令行开关优先级高于配置文件。这样即使项目配置 INSTALL_APK=1，
# 临时执行 --no-install 也能只构建和拉包，不会误装到当前连接的设备。
if [[ -n "$INSTALL_APK_CLI" ]]; then
  INSTALL_APK="$INSTALL_APK_CLI"
fi
if [[ -n "$DRY_RUN_CLI" ]]; then
  DRY_RUN="$DRY_RUN_CLI"
fi
if [[ -n "$DELETE_EXCLUDED_CLI" ]]; then
  DELETE_EXCLUDED="$DELETE_EXCLUDED_CLI"
  PRUNE_BUILD="all"
fi
if [[ -n "$PRUNE_BUILD_CLI" ]]; then
  PRUNE_BUILD="$PRUNE_BUILD_CLI"
fi
case "$SYNC_GIT_METADATA" in
  0|1) ;;
  *)
    echo "SYNC_GIT_METADATA 只能是 0 或 1：$SYNC_GIT_METADATA" >&2
    exit 1
    ;;
esac
case "$DELETE_EXCLUDED" in
  0|1) ;;
  *)
    echo "DELETE_EXCLUDED 只能是 0 或 1：$DELETE_EXCLUDED" >&2
    exit 1
    ;;
esac
# 旧配置只有 DELETE_EXCLUDED=0/1。没写 PRUNE_BUILD 时，1 表示清全部
# build/，0 表示只清已消失模块。新配置直接写 stale / all / off。
if [[ -z "$PRUNE_BUILD" ]]; then
  if [[ "$DELETE_EXCLUDED" == "1" ]]; then
    PRUNE_BUILD="all"
  else
    PRUNE_BUILD="stale"
  fi
fi
case "$PRUNE_BUILD" in
  stale|all|off) ;;
  *)
    echo "PRUNE_BUILD 只能是 stale、all 或 off：$PRUNE_BUILD" >&2
    exit 1
    ;;
esac
if [[ "$PRUNE_BUILD" == "all" ]]; then
  DELETE_EXCLUDED="1"
else
  DELETE_EXCLUDED="0"
fi

# 优先使用项目自己的 .remote-buildignore；如果项目还没初始化，则退回到
# 工具目录里的模板。这样可以直接 dry-run 一个未初始化项目，也能让项目
# 后续维护自己的排除规则。
IGNORE_FILE="${IGNORE_FILE:-$LOCAL_ROOT/.remote-buildignore}"
if [[ ! -f "$IGNORE_FILE" ]]; then
  IGNORE_FILE="$SCRIPT_DIR/remote-buildignore.template"
fi

# 只允许清理普通目录名，例如 build、.cxx。不要把路径、通配符或
# local.properties / .gradle 这类文件写进来，避免误删 SDK 配置。
prune_build_names=("${(@s: :)PRUNE_BUILD_NAMES}")
prune_build_names=("${(@)prune_build_names:#}")
if [[ ${#prune_build_names[@]} -eq 0 ]]; then
  echo "PRUNE_BUILD_NAMES 不能为空" >&2
  exit 1
fi
for prune_name in "${prune_build_names[@]}"; do
  if [[ ! "$prune_name" =~ '^[A-Za-z0-9._-]+$' ]]; then
    echo "PRUNE_BUILD_NAMES 只能是普通目录名，例如 build 或 .cxx：$prune_name" >&2
    exit 1
  fi
  case "$prune_name" in
    .|..|.git|.gradle|.mgit|.idea)
      echo "PRUNE_BUILD_NAMES 不能包含 $prune_name" >&2
      exit 1
      ;;
  esac
done

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

# rsync 排除了 **/build/ 这类中间产物目录，所以不会自己删它们。
# 关掉 overlay 或切分支后，本地模块没了，远端还留着这些目录，父目录
# 就删不掉。这里只处理 PRUNE_BUILD_NAMES 里的中间产物，绝不碰
# local.properties、.gradle/ 或其他 ignore 文件。
# stale：本地父目录已经不存在，把远端整个残留模块删掉。
# all：每个还在的模块也清掉这些中间产物目录，相当于远端 clean。
# off：完全不预清理，保持旧行为。
is_safe_relative_path() {
  local p="$1"
  [[ -n "$p" ]] || return 1
  [[ "$p" != /* && "$p" != *..* ]]
}

is_prune_build_dir() {
  local rel="$1"
  local name="${rel##*/}"
  local allowed
  for allowed in "${prune_build_names[@]}"; do
    if [[ "$name" == "$allowed" ]]; then
      return 0
    fi
  done
  return 1
}

# 本地已经没有这个模块时，沿着路径往上收到最高一层缺失目录。
# 例如远端还留着 story/lib-feed-story/build，本地整个 story/ 都没了，
# 就删 story/，而不是只删最底层那个 build。
stale_module_root() {
  local parent="$1"
  local best=""
  local cand="$parent"
  while [[ -n "$cand" ]]; do
    if [[ -e "$LOCAL_ROOT/$cand" ]]; then
      break
    fi
    best="$cand"
    if [[ "$cand" != */* ]]; then
      break
    fi
    cand="${cand%/*}"
  done
  print -r -- "$best"
}

collect_remote_build_prune_targets() {
  local mode="$1"
  local rel parent name stale name_pred
  local -a targets=()
  local prune_name

  if [[ "$mode" == "off" ]]; then
    return 0
  fi

  # 目录名已经校验过，只含字母数字、点、下划线和短横线，可以直接拼进远端 find。
  name_pred=""
  for prune_name in "${prune_build_names[@]}"; do
    if [[ -n "$name_pred" ]]; then
      name_pred+=" -o "
    fi
    name_pred+="-name $prune_name"
  done

  while IFS= read -r -d '' rel; do
    rel="${rel#./}"
    is_prune_build_dir "$rel" || continue
    name="${rel##*/}"
    if [[ "$mode" == "all" ]]; then
      is_safe_relative_path "$rel" || continue
      targets+=("$rel")
      continue
    fi
    parent="${rel%/$name}"
    # 工程根上的 build/ 本地父目录永远存在，默认保留给增量编译。
    [[ -n "$parent" && "$parent" != "$rel" ]] || continue
    is_safe_relative_path "$parent" || continue
    stale="$(stale_module_root "$parent")"
    if [[ -n "$stale" ]]; then
      targets+=("$stale")
    fi
  done < <(ssh "$REMOTE" "cd $remote_root_q && find . \\( -name .git -o -name .gradle \\) -prune -o -type d \\( $name_pred \\) -print0 -prune")

  targets=("${(u)targets[@]}")
  print -r -- "${(F)targets}"
}

prune_remote_build_targets() {
  local -a targets=()
  local p
  local label="$1"
  shift
  targets=("$@")
  if [[ ${#targets[@]} -eq 0 ]]; then
    return 0
  fi

  echo "$label：${#targets[@]} 个"
  for p in "${targets[@]}"; do
    echo "  $p"
  done
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "DRY_RUN=1：只列出远端中间产物清理目标，未删除。"
    return 0
  fi

  printf '%s\n' "${targets[@]}" | ssh "$REMOTE" "cd $remote_root_q && while IFS= read -r rel; do
    case \"\$rel\" in
      ''|/*|*..*) echo \"拒绝删除不安全路径：\$rel\" >&2; exit 1 ;;
    esac
    rm -rf -- \"\$rel\"
  done"
}

# --print-config 用于只读检查最终配置，不连接远端、不执行 rsync。
# 这能快速确认 CLI 参数覆盖、配置文件 source 和默认值是否符合预期。
print_config() {
  cat <<EOF
REMOTE=$REMOTE
LOCAL_ROOT=$LOCAL_ROOT
REMOTE_ROOT=$REMOTE_ROOT
REMOTE_COMMAND=$REMOTE_COMMAND
APK_GLOB=$APK_GLOB
LOCAL_APK_DIR=$LOCAL_APK_DIR
INSTALL_APK=$INSTALL_APK
SYNC_GIT_METADATA=$SYNC_GIT_METADATA
PRUNE_BUILD=$PRUNE_BUILD
PRUNE_BUILD_NAMES=$PRUNE_BUILD_NAMES
DELETE_EXCLUDED=$DELETE_EXCLUDED
ADB_SERIAL=${ADB_SERIAL:-}
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
# rsync 排除了 **/build/ 这类中间产物目录，所以不会自己清它们。
# 同步前按 PRUNE_BUILD 处理：stale 清本地已消失模块；all 清全部这些
# 目录；off 完全不预清理。local.properties、.gradle/ 一律保留。
# 首次使用前建议 DRY_RUN=1，确认排除规则不会删掉远端需要保留的文件。
if [[ "$SYNC_GIT_METADATA" == "1" ]]; then
  echo "[2/5] 同步源码和 Git 元数据"
else
  echo "[2/5] 同步源码（保留远端 Git 元数据）"
fi
case "$PRUNE_BUILD" in
  all) prune_label="清理远端全部中间产物目录（$PRUNE_BUILD_NAMES）" ;;
  stale) prune_label="清理远端已消失模块的残留中间产物（$PRUNE_BUILD_NAMES）" ;;
  *) prune_label="" ;;
esac
if [[ "$PRUNE_BUILD" == "off" ]]; then
  echo "PRUNE_BUILD=off：跳过远端中间产物预清理"
  prune_list=""
else
  prune_list="$(collect_remote_build_prune_targets "$PRUNE_BUILD")"
fi
prune_targets=("${(@f)prune_list}")
if [[ ${#prune_targets[@]} -eq 1 && -z "${prune_targets[1]}" ]]; then
  prune_targets=()
fi
prune_remote_build_targets "$prune_label" "${prune_targets[@]}"

rsync_args=(-az --delete-delay --human-readable)
if command rsync --info=help >/dev/null 2>&1; then
  rsync_args+=(--info=stats1,progress2)
else
  rsync_args+=(--stats)
fi

# 旧项目的 .remote-buildignore 可能仍排除了 .git/.mgit。默认同步 Git
# 元数据时，用先匹配的 include 规则覆盖旧排除项，让远端分支、HEAD、
# index 和本地一致；如果用户明确关闭，则显式排除，保留远端自己的 clone。
if [[ "$SYNC_GIT_METADATA" == "1" ]]; then
  rsync_args+=(
    "--include=.git"
    "--include=.git/***"
    "--include=**/.git"
    "--include=**/.git/***"
    "--include=.mgit"
    "--include=.mgit/***"
    "--include=**/.mgit"
    "--include=**/.mgit/***"
  )
else
  rsync_args+=(
    "--exclude=.git"
    "--exclude=.git/***"
    "--exclude=**/.git"
    "--exclude=**/.git/***"
    "--exclude=.mgit"
    "--exclude=.mgit/***"
    "--exclude=**/.mgit"
    "--exclude=**/.mgit/***"
  )
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
# REMOTE_COMMAND 在远端 REMOTE_ROOT 下由远端 shell 执行；SSH 非交互
# 会话通常不加载 alias，run64 这类入口需要在远端 PATH 上是真实命令。
echo "[3/5] 远端编译"
ssh "$REMOTE" "cd $remote_root_q && $REMOTE_COMMAND"

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
