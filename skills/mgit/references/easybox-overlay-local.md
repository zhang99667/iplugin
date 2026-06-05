# EasyBox overlay/local 上车配置

用于百度 EasyBox/xbuild 多仓工程中，根据实际代码改动仓库维护源码模式配置，减少开发分支上车和 master 合入之间反复手工切换 `syncSource` 的成本。

## 背景判断

常见目录含义：

- `xbuild/modules/default/*.gradle`：基础组件配置，描述组件名、层级、Maven 坐标、源码同步等信息。
- `xbuild/modules/overlay/*.gradle`：分支级覆盖配置，可以提交到 Git，会影响同一 topic/分支上的其他同学和 CI。
- `xbuild/modules/local/*.gradle`：个人本地覆盖配置，只用于本地开发，不应作为上 master 的提交内容。
- `repos/<层级>/<子仓库名>/...`：源码模式下的子仓库路径。

EasyBox 配置样例：

```gradle
modules {
    projects {
        business {
            feed {
                syncSource true
                revision "feed/11.x.x/feed00-xxxx/ref"
            }
        }
    }
}
```

- `syncSource true` 表示该模块按源码模式参与构建。
- `revision "..."` 是 CI 或配置侧的修订提示；本地已经 clone 的仓库不会仅因这里的 `revision` 自动切分支或更新代码，实际分支仍要用 MGIT/Git 验证。
- `business`、`service`、`basic`、`interfaces` 等通常是 EasyBox 层级；叶子节点通常是组件/仓库名，但必须与 MGIT 受管仓库交叉确认。

## 仓库 / 模块路径 / 文件映射

不要根据仓库名直接猜 EasyBox 文件名。映射必须从 `xbuild/modules` 现有配置中查出来。

常用查找命令：

```bash
find xbuild/modules -maxdepth 2 -type f -name 'modules*.gradle' -print
rg -n '^\s*<repo_or_module>\s*\{' xbuild/modules/default xbuild/modules/overlay xbuild/modules/local
rg -n 'absoluteRepo .*<repo_or_remote_name>' xbuild/modules/default
rg -n 'artifactId .*(<artifact>|<repo_or_module>)' xbuild/modules/default
```

映射时按证据优先级处理：

- `xbuild/modules/default/*.gradle` 是基础映射来源，先在这里确定仓库/模块属于哪个配置文件和模块路径。
- `absoluteRepo "ssh://.../<repo>"` 能直接证明远程仓库和 EasyBox 节点的关系。
- `repos/<层级>/<子仓库名>` 能辅助确定模块路径，例如 `repos/business/feed` 对应 `business.feed`。
- `xbuild/modules/local/*.gradle`、`xbuild/modules/overlay/*.gradle` 是覆盖层；如果其中已经有目标模块，优先更新现有节点。
- 同一个仓库可能有多个子组件或 artifact，不要把 `maven.artifactId` 当成仓库名；先回到父级 EasyBox 节点确认仓库。

输出或编辑前先整理映射表：

```text
仓库: lib_ad
模块路径: business.lib_ad
基础配置: xbuild/modules/default/modules-business-other.gradle
覆盖目标: xbuild/modules/local/modules-local-demo-dev.gradle 或 xbuild/modules/overlay/<target>.gradle
证据: absoluteRepo .../ad + 当前文件中 business { lib_ad { ... } }
```

示例映射（来自常见百度 App Android xbuild 结构，实际仍以当前工程为准）：

- `feed` -> `business.feed` -> `xbuild/modules/default/modules-business-feed.gradle`
- `lib_ad` / `lib_ad_runtime` / `ad_business` / `nadcore` -> `business.*` -> `xbuild/modules/default/modules-business-other.gradle`
- `im` -> `service.im` -> `xbuild/modules/default/modules-service-layer.gradle`

## 目标文件选择

先判断任务阶段：

- 开发分支上车、提测、topic 分支协作、需要 CI 或同分支同学使用源码模式：优先写 `xbuild/modules/overlay/*.gradle`。
- master 合入、上 master、合入前清理、用户明确说 overlay 不能带上：写入或保留 `xbuild/modules/local/*.gradle`，并确保 `xbuild/modules/overlay/*.gradle` 不在待提交改动中。
- 无法从用户意图、当前分支或 MGIT 状态判断阶段时，先问用户；不要猜。

判断当前阶段时优先结合：

```bash
mgit branch --compact
mgit status
git branch --show-current
```

若壳工程或主要仓库分支为 `master`，或用户语义是“合 master / 上 master”，按 master 合入处理。若是 feature/topic 分支且用户语义是“开发分支上车 / 提测 / CI 验证”，按开发分支处理。

## 从改动仓库推断模块范围

1. 用 MGIT 只读命令找实际改动仓库：

```bash
mgit status
mgit branch --compact
mgit -l
```

2. 将改动仓库映射到 EasyBox 模块路径和基础配置文件：

- 优先从 `repos/<层级>/<子仓库名>` 的路径推断，例如 `repos/business/feed` 对应 `business { feed { ... } }`。
- 如果只有仓库名，先在 `xbuild/modules/default/*.gradle` 中搜索仓库名、`absoluteRepo` 或组件名，记录命中的文件。
- 如果模块名和 MGIT 仓库名不一致，使用 `mgit info <repo>`、MGIT manifest、`repos/` 路径和 EasyBox 配置交叉确认。

3. 只为本次有代码改动、且需要源码模式参与构建的仓库生成配置；不要把全量 demo 配置照搬进去。

## 编辑规则

生成或更新目标文件时，保持最小配置：

```gradle
modules {
    projects {
        revision "master"

        business {
            feed {
                syncSource true
            }
        }
    }
}
```

- 开发分支 overlay：对本次改动仓库写 `syncSource true`；如 CI 需要指定组件分支，按当前仓库分支补 `revision "<branch>"`，但先确认这是用户需要的上车方式。
- master 合入 local：把仍需本地源码模式的模块写到 local 文件；不要把 overlay 作为 master 合入提交的一部分。
- 如果目标文件已有其他模块，保留无关配置，只更新本次相关模块。
- 如果已有 local/overlay 文件包含目标模块，优先更新该文件；否则根据用户指定文件或当前工程命名习惯创建/更新一个用途清晰的覆盖文件。不要仅凭 default 文件名推导 overlay/local 文件名。
- 不要修改 `default/*.gradle`，除非用户明确要求改基础组件配置。
- 不要因为 `syncSource false` 就清理、删除或跳过某仓；它只是构建配置。

## 上车前检查

开发分支上车前：

```bash
mgit status
git status --short xbuild/modules/overlay xbuild/modules/local
```

应确认：

- 本次改动仓库都在 EasyBox overlay 配置中开启源码模式。
- overlay 文件允许随开发分支提交。
- local 文件没有被误加入提交。

master 合入前：

```bash
mgit status
git status --short xbuild/modules/overlay xbuild/modules/local
```

应确认：

- overlay 文件没有待提交改动；如果有，应迁移到 local 或还原 overlay。
- local 文件可以保留个人配置，但不应进入 master 提交。
- 代码改动仓库仍按 MGIT 状态确认分支、冲突和未提交内容。

## 输出要求

完成判断或编辑后，总结：

- 判定阶段：开发分支上车或 master 合入。
- 修改的 EasyBox 文件：overlay 或 local 的具体路径。
- 根据哪些改动仓库生成了哪些模块路径，以及每个仓库命中的基础配置文件。
- 还有哪些 overlay/local 改动不能提交或需要用户确认。
