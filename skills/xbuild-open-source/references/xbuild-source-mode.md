# EasyBox/xbuild 源码模式打开规范

## 目标

把某个 EasyBox 模块从 Maven 依赖切到本地源码参与构建，通常是在 `xbuild/modules/local/*.gradle` 或 `xbuild/modules/overlay/*.gradle` 中补：

```gradle
modules {
    projects {
        revision "master"

        underlayers {
            containers {
                talospro {
                    syncSource true
                }
            }
        }
    }
}
```

## 目录语义

- `xbuild/modules/default/*.gradle`：基础模块映射，包含层级、模块名、`absoluteRepo`、`projectPath`、Maven 坐标；只读定位为主。
- `xbuild/modules/local/*.gradle`：个人本地覆盖，适合本地调试和 master 合入前保留源码模式；不要提交到公共分支。
- `xbuild/modules/overlay/*.gradle`：分支级覆盖，适合开发分支上车、CI、同分支同学共用；可能进入提交。
- `repos/<层级>/<仓库名>`：源码模式同步后的本地仓库目录。

## 判断要打开哪个模块

按证据优先级定位，不要凭经验硬猜：

1. 用户明确给出模块路径或覆盖文件：优先采用。
2. 用户给类名/方法名/包名/崩溃栈：先在 `repos` 和当前工程里搜源码。
3. 如果源码不存在，搜 `xbuild/modules/default` 的 `absoluteRepo`、模块名、artifactId、groupId。
4. 如果只能看到 AAR/Maven 坐标，从 Gradle 依赖名反查 default 映射。
5. 如果命中多个配置块，列出候选，不直接编辑。

常用只读命令：

```bash
rg -n "目标类名|方法名|包名" repos app xbuild
rg -n "absoluteRepo .*<repo>|<module> \\{|artifactId '(<artifact>)'" xbuild/modules/default
sed -n '<start>,<end>p' xbuild/modules/default/<file>.gradle
find repos -maxdepth 5 -type d -iname '*keyword*'
```

## 从崩溃栈反查的做法

先把栈拆成业务层、SDK Java 层、native 层：

- 业务类命中本地 `repos/business/...`：说明业务仓已经开或已同步。
- `com.baidu.talospro.core.sdk.*`、`RenderContainer`、`nativeDestroyContainer`、`libtalospro_android.so`：优先查 `underlayers.containers.talospro`，远端通常是 `baidu/baiduapp-android/talospro-interface`。
- `com.baidu.searchbox.containers.talospro.*`、手百宿主适配：查 `underlayers.containers.bba_talospro`，远端通常是 `baidu/baiduapp-android/bba-talospro`。
- 广告业务常见仓：`business.ad_business`、`business.lib_ad_runtime`、`business.lib_ad`、`business.nadcore`，但必须用当前工程 default 配置确认。

示例证据链：

```text
AdTalosComponent.kt 命中 repos/business/ad_business/flowvideo
AdTalosViewManager.kt 命中 repos/business/lib_ad_runtime/lib-ad-runtime
RenderContainer / TalosProView / libtalospro_android.so 未命中本地源码
xbuild/modules/default/modules-underlayers-containers.gradle 命中:
  underlayers.containers.talospro
  absoluteRepo "ssh://icode.baidu.com:8235/baidu/baiduapp-android/talospro-interface"
结论：需要打开 underlayers.containers.talospro
```

## 编辑覆盖文件

用户指定文件时，按指定文件编辑。例如 `xbuild/modules/local/modules-local-demo-all.gradle`：

```gradle
underlayers {
    containers {
        talospro {
            syncSource true
        }

        lightbrowser {
            syncSource true
        }
    }
}
```

规则：

- 保持现有缩进和层级风格。
- 只补目标节点，不格式化整文件。
- 已有 `syncSource false` 的目标模块，按用户要求改为 `true`。
- 已有其他模块配置时保留，不删除。
- 如果父层级不存在，补最小父层级。
- 如果 `projects { revision "..." }` 已存在，保留；没有且需要新建完整文件时按当前壳工程主分支选择，无法判断时问用户。

## 是否需要 MGIT

改 `syncSource true` 只表示构建希望使用源码模式，不一定已经把仓库同步到 `repos`。

### 先判断当前状态

把 default 中的模块映射、覆盖配置和本地目录交叉检查后再动作：

| `syncSource` | 本地源码目录 | 处理方式 |
|---|---|---|
| `true` | 存在 | 不改配置、不重复同步，直接继续原任务 |
| `true` | 不存在 | 不改配置，只精确同步目标仓 |
| `false` 或未配置 | 存在 | 代码阅读可直接继续；用户要求源码构建时才改为 `true` |
| `false` 或未配置 | 不存在 | 唯一映射时补个人 local 的 `syncSource true`，再精确同步目标仓 |

检查 local 和 overlay 时要记录命中的具体文件。个人调试或其他代码任务中隐式发现源码缺失时，默认写现有个人 local 文件；如果存在多个 local 文件，优先选择当前构建已引用或与壳工程/场景命名匹配的文件，无法确定哪个生效时再询问。只有用户明确要求开发分支上车、CI 共用或指定 overlay，才修改公共 overlay。

源码已存在时，“继续原任务”优先级高于整理构建配置。代码阅读不依赖 `syncSource true`；不要因为配置没开而打断已经可以进行的源码分析。

在需要实际拉取源码时，先做 MGIT 预检：

```bash
which mgit
ruby -v
ruby -e 'require "colored2"; require "peach"; require "tty-pager"; require "logger"; puts "mgit ruby deps ok"'
```

预检失败时，不继续执行 MGIT；报告缺少的 gem。预检通过后先用只读命令确认 MGIT 工作区和精确仓库名：

```bash
mgit -w
mgit -l
mgit -al
mgit info <exact-repo>
```

`absoluteRepo` 是远端映射证据，不保证它的末段就是 MGIT 参数。必须用 `mgit -al` 或 `mgit info` 验证 `<exact-repo>`，不能从 URL 短名直接猜。

用户明确要求“开源码”，或代码阅读、排障、修改任务已经因目标源码缺失而无法继续时，视为已授权补齐这个唯一目标仓。执行：

```bash
mgit sync -c <exact-repo>
```

该例外只覆盖“本地缺失 + 唯一映射 + 精确仓库”的下载动作。以下操作仍要先说明影响范围并等待确认：

- 不带精确仓库的 `mgit sync`、`mgit sync -n` 或批量同步。
- 对已有仓执行 pull、同步更新或切分支。
- 清理、reset、删除、跨仓自定义命令。

同步完成后检查 default 映射预期的 `repos/<层级>/<仓库>` 目录是否出现。若精确同步失败，报告命令和错误，保留已写的 local 配置，不要自动扩大到全量同步。

## 汇报格式

完成后简洁汇报：

```text
已打开 <module-path> 源码模式。
覆盖文件：<path>
证据：<default-file>:<line> absoluteRepo ...
本地源码目录：repos/<...>（原本存在/已精确同步/同步失败）
原任务：已继续处理/因 <具体原因> 阻塞
```
