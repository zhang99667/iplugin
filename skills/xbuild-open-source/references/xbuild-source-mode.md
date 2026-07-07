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

在需要实际拉取源码时，先做 MGIT 预检：

```bash
which mgit
ruby -v
ruby -e 'require "colored2"; require "peach"; require "tty-pager"; require "logger"; puts "mgit ruby deps ok"'
```

预检失败时，不继续执行 MGIT；报告缺少的 gem。预检通过后才考虑只读命令：

```bash
mgit -l
mgit status
mgit branch --compact
```

执行 `mgit sync`、切分支、清理、reset、跨仓命令前必须说明影响范围并等待用户确认。

## 汇报格式

完成后简洁汇报：

```text
已打开 <module-path> 源码模式。
覆盖文件：<path>
证据：<default-file>:<line> absoluteRepo ...
本地源码目录：repos/<...>（存在/尚未同步）
下一步：如目录尚不存在，需要 MGIT 同步该仓。
```
