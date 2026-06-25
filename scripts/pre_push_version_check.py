#!/usr/bin/env python3
"""push 前版本防撞检查。

这个脚本给 Git pre-push hook 使用：先 fetch 远端 tracking 分支，再确认本地
将要 push 的提交已经包含远端最新提交，并且插件 manifest 版本号大于远端版本。
如果远端已经出现同版本 CHANGELOG 或 versions 记录，也会拒绝 push。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = (
    ".claude-plugin/plugin.json",
    ".codex-plugin/plugin.json",
)
CHANGELOG = "CHANGELOG.md"
ZERO_OID = "0" * 40
SEMVER_RE = re.compile(r"^([0-9]+)\.([0-9]+)\.([0-9]+)$")


class GuardError(RuntimeError):
    """可直接展示给用户的版本防撞失败原因。"""


@dataclass(frozen=True)
class RefUpdate:
    """Git pre-push 从 stdin 传入的一条 ref 更新记录。"""

    local_ref: str
    local_oid: str
    remote_ref: str
    remote_oid: str


def git(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    """在仓库根目录执行 git 命令，并捕获 stdout/stderr 供后续判断。"""

    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def git_text(args: list[str]) -> str:
    """执行 git 命令并返回去掉首尾空白后的 stdout。"""

    return git(args).stdout.strip()


def git_ok(args: list[str]) -> bool:
    """执行 git 命令，只关心退出码是否为 0。"""

    return git(args, check=False).returncode == 0


def parse_ref_updates(stdin_text: str) -> list[RefUpdate]:
    """解析 pre-push stdin 中的 ref 更新列表。"""

    updates: list[RefUpdate] = []
    for raw_line in stdin_text.splitlines():
        # Git pre-push 每行固定 4 列：本地 ref / oid / 远端 ref / oid。
        # 非标准行直接忽略，避免 hook 因额外输出格式崩掉。
        parts = raw_line.split()
        if len(parts) != 4:
            continue
        updates.append(RefUpdate(*parts))
    return updates


def current_branch() -> str | None:
    """返回当前分支名；detached HEAD 时返回 None。"""

    result = git(["symbolic-ref", "--quiet", "--short", "HEAD"], check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def choose_ref_update(updates: list[RefUpdate]) -> RefUpdate | None:
    """从 pre-push 更新列表里选择最应该检查的一条分支更新。"""

    branch = current_branch()
    if branch:
        current_ref = f"refs/heads/{branch}"
        for update in updates:
            # 优先检查当前分支的 push。删除远端分支时 local_oid 是全 0，
            # 这种操作没有本地版本号可比，后面会跳过。
            if update.local_ref == current_ref and update.local_oid != ZERO_OID:
                return update
    for update in updates:
        # 如果一次 push 多个分支但不包含当前分支，退而求其次检查第一条
        # 非删除更新，至少拦截常见的版本号重复提交。
        if update.local_oid != ZERO_OID:
            return update
    return None


def remote_name_from_args(args: list[str]) -> str:
    """从 hook 参数或 upstream 推断远端名，默认使用 origin。"""

    if args and not args[0].startswith("-"):
        return args[0]
    upstream = upstream_ref()
    if upstream and "/" in upstream:
        return upstream.split("/", 1)[0]
    return "origin"


def upstream_ref() -> str | None:
    """返回当前分支配置的 upstream，例如 origin/main。"""

    result = git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def ref_exists(ref: str) -> bool:
    """检查一个 ref 是否能解析为 commit。"""

    return git_ok(["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"])


def remote_tracking_ref(remote: str, remote_ref: str) -> str | None:
    """把远端真实 ref 转成 fetch 后的本地 tracking ref。"""

    prefix = "refs/heads/"
    if not remote_ref.startswith(prefix):
        return None
    branch = remote_ref[len(prefix) :]
    candidate = f"refs/remotes/{remote}/{branch}"
    return candidate if ref_exists(candidate) else None


def choose_compare_ref(remote: str, update: RefUpdate | None) -> str:
    """选择用于版本比较的远端 tracking ref。"""

    candidates: list[str] = []
    if update:
        # pre-push 会告诉我们这次要更新哪个远端分支；优先比较同一个
        # 远端分支，避免在非 main 分支 push 时误拿 main 做判断。
        tracking = remote_tracking_ref(remote, update.remote_ref)
        if tracking:
            candidates.append(tracking)
    upstream = upstream_ref()
    if upstream:
        # 如果 hook stdin 不完整或手动运行脚本，就退回当前分支 upstream。
        candidates.append(upstream)
    candidates.extend([f"refs/remotes/{remote}/main", "origin/main"])

    seen: set[str] = set()
    for candidate in candidates:
        # 候选列表可能重复，例如 upstream 本来就是 origin/main；
        # 去重后按优先级选择第一个真实存在的 ref。
        if candidate in seen:
            continue
        seen.add(candidate)
        if ref_exists(candidate):
            return candidate
    raise GuardError("找不到可比较的远端分支，无法确认版本号是否冲突。")


def fetch_remote(remote: str) -> None:
    """拉取远端最新状态；测试时可通过环境变量跳过网络访问。"""

    if os.environ.get("IPLUGIN_PRE_PUSH_SKIP_FETCH") == "1":
        return
    # 这里只 fetch，不自动 pull/rebase。hook 自动改分支历史或工作树
    # 会让失败状态难以恢复；我们只拿最新远端状态来做拦截。
    result = git(["fetch", "--quiet", "--prune", remote], check=False)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        detail = f"\n{stderr}" if stderr else ""
        raise GuardError(f"拉取远端状态失败，无法确认版本号是否冲突。{detail}")


def commit_id(ref: str) -> str:
    """把 ref 解析为 commit id。"""

    return git_text(["rev-parse", "--verify", f"{ref}^{{commit}}"])


def is_ancestor(ancestor: str, descendant: str) -> bool:
    """判断 ancestor 是否已经包含在 descendant 的历史里。"""

    return git_ok(["merge-base", "--is-ancestor", ancestor, descendant])


def show_file(ref: str, path: str) -> str:
    """读取指定 ref 中某个文件的内容。"""

    result = git(["show", f"{ref}:{path}"], check=False)
    if result.returncode != 0:
        raise GuardError(f"{ref} 缺少 {path}，无法确认版本号。")
    return result.stdout


def parse_semver(version: str) -> tuple[int, int, int]:
    """把 X.Y.Z 版本号转换成可比较的三元组。"""

    match = SEMVER_RE.match(version)
    if not match:
        raise GuardError(f"插件版本 {version!r} 不是 X.Y.Z 格式。")
    return tuple(int(part) for part in match.groups())


def manifest_version(ref: str) -> str:
    """读取某个提交里的插件 manifest 版本，并检查两端 manifest 一致。"""

    versions: list[tuple[str, str]] = []
    for path in MANIFESTS:
        # Claude / Codex 两份 manifest 共用同一个插件版本号；
        # 任一文件格式错误或缺 version，都不能继续判断冲突。
        try:
            data = json.loads(show_file(ref, path))
        except json.JSONDecodeError as exc:
            raise GuardError(f"{ref}:{path} 不是合法 JSON：{exc}") from exc
        version = data.get("version")
        if not isinstance(version, str) or not version:
            raise GuardError(f"{ref}:{path} 缺少非空 version 字段。")
        parse_semver(version)
        versions.append((path, version))

    unique = {version for _, version in versions}
    if len(unique) != 1:
        # 两份 manifest 已经不一致时，继续比较远端只会给出误导结果。
        detail = ", ".join(f"{path}={version}" for path, version in versions)
        raise GuardError(f"{ref} 的两个 manifest 版本不一致：{detail}")
    return versions[0][1]


def path_exists(ref: str, path: str) -> bool:
    """检查某个 ref 中是否存在指定路径。"""

    return git_ok(["cat-file", "-e", f"{ref}:{path}"])


def changelog_has_version(ref: str, version: str) -> bool:
    """检查 CHANGELOG 是否已经声明某个版本。"""

    text = show_file(ref, CHANGELOG)
    # `]` 和空格都不是单词字符，不能用 `\b` 判断标题边界；
    # 这里明确要求版本号后面是空白或行尾，匹配 `## [0.19.18] - ...`。
    pattern = re.compile(rf"^## \[{re.escape(version)}\](?:\s|$)", re.MULTILINE)
    return bool(pattern.search(text))


def check_versions(local_ref: str, compare_ref: str) -> None:
    """执行本地提交与远端 tracking ref 的完整版本防撞检查。"""

    local_commit = commit_id(local_ref)
    remote_commit = commit_id(compare_ref)
    if local_commit == remote_commit:
        # 没有比远端多任何提交时，说明这次不会产生新的插件版本。
        return

    if not is_ancestor(compare_ref, local_commit):
        # 远端有本地未包含的提交时，最容易出现“我和别人都用了同一个
        # 下一个版本号”的情况，必须先同步远端再重新决定版本。
        raise GuardError(
            f"远端 {compare_ref} 有本地未包含的提交。请先执行 git pull --rebase "
            "或 git pull --ff-only，再重新选择版本号后 push。"
        )

    local_version = manifest_version(local_commit)
    remote_version = manifest_version(compare_ref)

    if parse_semver(local_version) <= parse_semver(remote_version):
        # SemVer 三元组比较可以正确处理 0.19.10 > 0.19.9。
        raise GuardError(
            f"本地插件版本 {local_version} 没有大于远端 {compare_ref} 的版本 "
            f"{remote_version}，存在版本号撞车风险。请先更新版本号、CHANGELOG 和 versions 记录。"
        )

    version_doc = f"versions/v{local_version}.md"
    version_dir = f"versions/v{local_version}"
    # manifest 版本大于远端版本仍不够：远端可能已经有同版本文档或
    # CHANGELOG 条目但 manifest 还没更新，这里额外拦一次重复占用。
    if path_exists(compare_ref, version_doc) or path_exists(compare_ref, version_dir):
        raise GuardError(f"远端已存在 {version_doc} 或 {version_dir}/，不能重复使用版本号 {local_version}。")

    if changelog_has_version(compare_ref, local_version):
        raise GuardError(f"远端 CHANGELOG 已存在 [{local_version}] 条目，不能重复使用该版本号。")

    if not path_exists(local_commit, version_doc) and not path_exists(local_commit, version_dir):
        # 本地也必须有版本规划文档，保持仓库原有发布记录规则。
        raise GuardError(f"本地版本 {local_version} 缺少 {version_doc} 或 {version_dir}/。")

    if not changelog_has_version(local_commit, local_version):
        # CHANGELOG 是人读入口，不能只改 manifest。
        raise GuardError(f"本地 CHANGELOG 缺少 [{local_version}] 条目。")

    print(
        f"PASS  pre-push version check: local {local_version} > "
        f"{compare_ref} {remote_version}"
    )


def main(argv: list[str]) -> int:
    """脚本入口：兼容 Git hook 调用和手动运行。"""

    args = [arg for arg in argv[1:] if arg != "--no-fetch"]
    if "--no-fetch" in argv[1:]:
        # 本地调试时可以避免网络访问；真实 hook 默认必须 fetch。
        os.environ["IPLUGIN_PRE_PUSH_SKIP_FETCH"] = "1"

    updates = parse_ref_updates(sys.stdin.read())
    update = choose_ref_update(updates)
    if updates and update is None:
        # 全是删除远端 ref 的 push，不涉及新插件版本。
        print("PASS  pre-push version check: only deleted refs, nothing to verify")
        return 0

    remote = remote_name_from_args(args)
    try:
        fetch_remote(remote)
        compare_ref = choose_compare_ref(remote, update)
        # 真正的 pre-push 使用 Git 传入的 local_oid；手动运行时没有
        # stdin，就检查当前 HEAD，便于在 commit 后 push 前预跑。
        local_ref = update.local_oid if update else "HEAD"
        check_versions(local_ref, compare_ref)
    except GuardError as exc:
        print(f"ERROR pre-push version check failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
