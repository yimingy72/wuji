# Phase 1A 收口与集成验收

- 状态：approved / in-progress
- 批准：2026-09-09 用户明确要求 IMPLEMENT THIS PLAN，覆盖本文件及 Spec §8。
- 阶段：Phase 1A；继续使用既定工具链、OpenAPI 0.2.0、Docker Desktop Kubernetes、固定端口和五套主题。阶段验收前不进入 Phase 1B。
- 起点：主阶段已集成存储/主题；API `955045644d2ab4b886ecff58018da0e43bae4017`、WEB `d201cde8faf40846f4c52329b6410b78a5d361ab`、TEST `0b194da668790870dd276b276cd339f14e47f114` 作为已交付批次集成。

## 1. 修正与接口

身份完成事务在用户 advisory lock 后，先条件 UPDATE/RETURNING 消费未过期的 exchanging 握手，再撤销旧会话、插入新会话并追加审计；这些写入同事务提交。条件不命中使用明确的握手失效结果，回调303到 UNAUTHENTICATED，不能混为身份未预置的 FORBIDDEN 或依赖503。旧过期/被取代交换的成功、失败响应都不能修改新的握手或应用会话 Cookie。协议仍复用 Authlib 严格校验，无测试认证旁路。

初始化撤销 PUBLIC 和两个运行角色的 TEMPORARY，并验证普通/临时建表、越权读取仍被拒绝；使用现有专属DB幂等修复，不删表或重新播种来掩盖问题。

生命周期在 apply 前检查所有将修改的 Namespace、Secret、Deployment、Service、ConfigMap、PVC；仅明确NotFound视作不存在，其他错误原样按安全错误类型失败。重建只删除已验证name/UID的本项目Pod。普通停止保留Kubernetes资源、Secret、PVC及已有DB/realm。

子进程spawn后立即登记PID、实际进程组、启动标识和精确命令归属，再等待就绪；失败路径有本次句柄可清理。终止前重新核对实际进程组与归属。运行记录读改写使用独立互斥锁和原子替换，避免supervisor/控制命令覆盖彼此记录。SIGINT/SIGTERM从启动阶段起统一处理，测试子进程也受监督；子进程异常退出和启动失败均非零退出并写报告。转发有界退避，paused状态阻止自动恢复。

私有run-file保持schema v1和0600，入口验证当前用户、绝对路径、worktree、候选SHA、profile/namespace/端口组合；需要JSON Schema库时显式复用已冻结的jsonschema 4.26.0。API环境只注入auth/project DSN、应用签名密钥和OIDC客户端配置，不接收管理凭据或私有run文件。控制入口保留 `control.sh --run-file <absolute> <command>`，成功使用 `{ok:true,run_id,result}`，失败stderr输出脱敏JSON与非零退出；既有测试辅助层解包result。

保留 `dev:infra`、`dev:seed`、`dev:platform`、`dev:down`、`test:platform`。增加 `test:platform:lifecycle` 独立检查入口；内部 `test-platform --serve-only` 与完整测试共享准备、监督和清理路径，在就绪后等待控制或信号，不执行递归测试。公开业务API不增加测试控制接口。

WEB保留真实API查询和主题行为，精简登录页解释为必要标题、组织账号登录操作及错误提示；不显示内部权限码/版本/契约。临时QA夹具不得占用8000等正式集成端口；临时验证使用事先确认空闲的非保留端口并记录、清理自身进程。

## 2. 分工与交付顺序

主代理保存A的未提交生命周期草稿，更新阶段文档并集成三份交付；为各任务固定统一SHA。原工作树及忽略目录中的证据保留，不能覆盖丢失。

| 负责人 | 模型 | 唯一修改范围 | 交付 |
| --- | --- | --- | --- |
| A | gpt-5.6-sol / xhigh | apps/api、infra/kubernetes、scripts/platform；全部manifest/锁文件、迁移、契约和根命令 | 先身份/TEMP修正，再完整lifecycle/control/schema及开发检查 |
| B | gpt-5.6-sol / xhigh | apps/web非manifest配置/源码、packages/theme/src；确有需要时原型主题导入 | 文案与真实API联调修复；不引入Mock到正式构建 |
| T | gpt-5.6-sol / high | tests/api、tests/platform-browser、tests/platform-lifecycle、tests/fixtures/oidc、playwright.platform.config.ts、independent-test.md | 独立补例；基于最终集成SHA执行并报告 |
| 主代理 | 当前主模型 | 文档、集成、审查与验收 | 核查差异、证据和关键用户路径，最后更新master |

A/T先对齐serve-only就绪事件和run-file读取方式，沿用已定控制命令；测试的确定性屏障由受控issuer与测试DB事务实现，不进入业务认证路径。A/B只做分配范围，公共变更A先交付、主代理集成后其余任务同步。最终执行期间候选工作树不能漂移。

## 3. 验证与验收

依次完成冻结安装、`pnpm check:platform`、正式构建、`pnpm test:platform:lifecycle` 和 `pnpm test:platform`。独立用例在现有67个API/14个浏览器基础上补齐：旧交换仍在飞时过期并释放、保留新握手；用户登录/禁用确定性竞争；两角色TEMP拒绝；端口冲突、错误归属拒绝、启动/子进程失败、SIGINT/SIGTERM、运行文件更新竞争及finally清理。

错误归属拒绝可以使用独立Kubernetes命令夹具，验证无写操作发出；不修改真实他人资源。生命周期真实进程检查使用本项目独占run，父测试进程观察子run退出后确认端口/锁可复用、DB/realm保留。测试新建run数据库，不清空上一run或开发数据；数据库失联、API重启、Pod重建及恢复必须在同一run中用原会话/项目取证。

开发者自测与测试收集成功不等于平台通过。独立报告绑定实际SHA、run_id、环境、命令、退出码、通过/失败/skip数及ignored证据；关键skip或缺证据仍失败。主代理亲自复核登录、撤权、退出失败恢复和主题，完整P1A-01–10通过后才合入master。原型12/12回归保留既有证据，相关代码变化时再复测。

最终交付正式本地工作台入口、启动/停止说明、凭据安全读取方式、已测试代码SHA与验收记录；记录提交与代码SHA分别标明。本文件不宣称完整Phase1或Agent执行能力已交付。
