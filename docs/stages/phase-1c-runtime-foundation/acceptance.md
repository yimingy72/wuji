# 单 Task Pod 执行基础验收

- 本批基础库结论：accepted / offline checks passed；日期：2026-09-11。
- 真实集群/运行链路：not-tested，未接正式API/Cairn/Pi/MCP，不代表完整Runtime已验收。
- 被测候选：026457fc7c3df5c6feb46a75211715b9a919b4ae；分支codex/phase-1c-runtime-foundation。
- run_id：runtime-foundation-20260911。
- 起始基准：eee81b4746a27cba633769c3cdf0fcdf60198028及用户确认的单Pod架构修订。
- [Spec](spec.md)、[Plan](plan.md)。记录提交通过git log查询，不回填自身SHA。
- 实现与审查：主代理设计/模型/控制器/SDK适配/测试集成；gpt-6-astra/low按明确范围实现manifest及对应测试，主代理复核并修正。测试由当前会话执行，不称为独立测试。

## 1. 实际结果

| 编号 | 结果 | 证据与边界 |
| --- | --- | --- |
| R01 | passed | 两容器、独立digest镜像/Secret/PVC、受管安全字段；合法默认字段/排序/资源Quantity规范化可复用；镜像、权限、归属、凭据及额外容器/env漂移拒绝 |
| R02 | passed | 缺失/过期/epoch或Scope不符不创建；创建后许可撤销按返回自有UID请求停止；真实许可存储和事务仍待控制面接入 |
| R03 | passed | 自有Pod复用，其他代次或错误归属阻止创建；403读取错误不当成不存在；创建409只核对已有对象 |
| R04 | passed | UID/resourceVersion条件删除，错误UID不删除；接受删除为stopping，后续404才确认资源不存在；不推导实际进程/目标/出口已停止 |
| R05 | passed | 官方Kubernetes SDK配置retries=0、有限请求超时；API替身核对V1DeleteOptions/V1Preconditions、404/403/500处理和Secret值不返回 |

一次定向执行25个用例通过，pytest报告用例耗时0.08秒；包含解释器/导入的子进程墙钟耗时见下表。没有扩展旧API、浏览器、主题、长时间故障或模型矩阵。

## 2. 环境、命令和退出码

Python3.13.15；仓库现有uv0.12.11及缓存；本工作树独立.venv，未更改主业务工作区环境。下表uv通过主目录work/toolchain/bin/uv运行，--directory指向本工作树；缓存和受管Python路径沿用主目录工具链。

| 命令 | 退出码 | 命令墙钟秒数 |
| --- | --- | --- |
| `uv lock` | 0 | 9.474 |
| `uv sync --frozen --group task-runtime` | 0 | 14.221 |
| `.venv/bin/python -m pytest packages/task-runtime/tests -q` | 0 | 4.574 |
| `uv build --package wuji-task-runtime --out-dir artifacts/phase-1c-runtime-foundation/dist` | 0 | 0.792 |

锁文件新增任务基础包及Kubernetes依赖；逐项核对旧锁定包的name/version集合全部保留，未升级P0/已有API依赖。源码包和wheel已生成于忽略的artifacts目录。日志和原始计时报告：`artifacts/phase-1c-runtime-foundation/validation.json`及lock/sync/unit/build.log。

## 3. 共享检查预算

- 完整窗口UTC：2026-09-10T16:16:32.661212+00:00 → 2026-09-10T16:17:53.843522+00:00；本地时间为2026-09-11。
- 本批完整窗口向上取整 **82秒**，包含依赖准备、候选提交/等待、检查；不是只相加成功命令的耗时。
- 承接P0已用426秒，累计 **508/600秒**，剩余 **92秒**；不得按后续批次或代理重置。
- 本批真实模型调用0次、Kubernetes集群调用0次、目标请求0次。P0原4次真实额度已耗尽，记录和账本不改写。
- 通过后停止追加测试；后续仅文档记录/导航修订，不改变被测运行源码或宣称新源码实测。

## 4. 主代理复核与交付

核对单Pod唯一资源所有权、每次执行许可绑定、返回UID条件清理、Secret/卷隔离及官方SDK调用边界。静态审查时补充资源Quantity语义规范化、明确fsGroup/镜像拉取策略和许可源不可用时拒绝执行，这些均在被测候选内；没有测试失败复跑。

本批只交付独立wuji-task-runtime基础包：配置、Pod模板/归属、创建复用、基础设施观察及条件停止。导入不读取kubeconfig或连接集群；官方客户端必须由调用方显式配置。公开API仍0.4.0，现有Task/数据库迁移/前端均未修改，主工作区HEAD和master不前移。Cairn黑板核心未下载修改。

## 5. 延期与实际限制

- Task权威存储中的许可和独占执行租约、0.5业务接口/迁移、持续调谐服务尚未接入。Python许可对象不是外部身份认证，list/check/create不是跨数据库和Kubernetes的原子事务。
- 镜像构建、ConfigMap/Secret/PVC准备、UID/fsGroup存储兼容和真实Pod调度/就绪未验证。基础设施ready不表示MCP、模型或出口可执行。
- Cairn在agent容器动态启动/停止进程、Pi工具白名单/MCP往返、共享Kali目录操作和Artifact归档未接入。
- Pod删除的API接受或资源404不证明目标操作结果或出口断流；真实停止必须后续独立核对。
- NetworkPolicy/受控出口、真实模型/金额限制和长上下文/恢复未验收；不能据此开放真实目标或把未知结果写成未复现。

后续先接控制面权威记录与资源准备，再接Cairn执行后端和工具；仍沿用剩余预算和原调用限制。
