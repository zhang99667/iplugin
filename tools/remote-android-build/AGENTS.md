# remote-android-build 维护指南

这个目录是 iPlugin 下的独立工具子项目，用于把本地 Android 工程同步到远端 Mac 编译，再把 APK 拉回本地安装。维护时遵循本文件，同时继续遵循仓库根目录的 `AGENTS.md`。

## 目录约定

- `remote-build.zsh`：主入口，执行配置加载、rsync 同步、远端 Gradle 构建、APK 拉回和本地安装。
- `init-project.zsh`：项目初始化入口，给 Android Gradle 工程生成 `.remote-buildignore` 和 `.remote-build.zsh`。
- `remote-buildignore.template`：默认 rsync 排除规则。
- `remote-build.env.example`：配置示例，方便用户复制或对照。
- `README.md`：面向使用者的中文说明。
- `CHANGELOG.md`：工具级变更日志。
- `docs/`：设计、实施方案和排查文档。
- `versions/`：每个工具版本的目标、变更、决策和验证记录。

## 维护原则

- 这个工具只实现 P0 远程构建闭环：SSH、rsync、远端 Gradle、本地 adb。
- 不在本工具里默认引入 Mutagen、Gradle Remote Cache、Tailscale 或 VNC。
- 不把工程私有配置、签名文件、证书、`local.properties` 同步到远端镜像目录。
- 默认脚本必须可读、可审计，复杂项目差异放在 `.remote-build.zsh` 配置里，不在主脚本里硬编码某个业务仓库。
- `CLAUDE.md` 与 `AGENTS.md` 必须保持一致。

## 提交流程

1. 修改脚本后运行：

```bash
zsh -n tools/remote-android-build/init-project.zsh
zsh -n tools/remote-android-build/remote-build.zsh
```

2. 修改插件仓库内容后运行：

```bash
python3 scripts/validate-plugin.py
```

3. 如新增或改变用户可见行为，更新：

- `README.md`
- `CHANGELOG.md`
- `versions/vX.Y.Z.md`
- `versions/README.md`
- 必要时补充 `docs/`

4. 提交时只暂存 `tools/remote-android-build/` 相关文件，不带入仓库里其他未提交改动。

## 风险边界

- `rsync --delete-delay` 会删除远端镜像中本地已不存在的文件；首次运行必须建议用户先执行 `DRY_RUN=1`。
- `REMOTE_ROOT` 必须被视为可丢弃镜像，不应存放远端私有 secrets。
- `adb install -r -d` 只覆盖普通 debug 安装场景；split APK、AAB、签名冲突需要项目配置或人工处理。
