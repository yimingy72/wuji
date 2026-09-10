# Phase 1C 前置 P0 Plan

- 状态：completed；本批P0已交付，后续0.5业务仍未批准。批准依据同Spec。
- 背景：根AGENTS、project-context、agent-harness-decision、architecture中Model Gateway/QuotaGroup、模型网关历史实测；最新用户批准计划为本批范围依据。

## 顺序与唯一归属

1. 主代理从381ae3a创建 `work/worktrees/phase-1c-prep` / `codex/phase-1c-prep`。显式复制8dcf7ec的根AGENTS/DESIGN/PRODUCT/README及有差异的docs Markdown清单；排除全部spikes源码。更新索引指向本树、提交文档基线。
2. SOL/xhigh 在 `work/worktrees/phase-1c-prep-adapter` / `codex/phase-1c-prep-adapter` 开发，独占 `packages/agent-integration/**`、根 `pyproject.toml` / `uv.lock`。不修改apps/API/契约/前端/迁移/生命周期/根pnpm命令。
3. 集成包采用src布局，入口 `python -m wuji_agent_integration.probe`，输入私有凭据文件路径、共享调用账本、输出报告路径；不接入正式API。根uv workspace增加成员，模型依赖只通过显式agent-validation组/包安装，普通API不加载这些依赖。
4. Harness与Provider通过进程IPC和框架消息序列化交接；每个验证子流程调用次数有局部2次上限且共用持久4次账本；Provider发送前检查截止时间/次数，预登记attempt，错误不返回密钥、请求头或原始异常。
5. 开发者只做静态检查与依赖导入/工具清单检查，不调用真实模型。依赖准备每段由主代理记录开始/结束累计时间，提供一次安装后的同一环境给最终集成候选，禁止重复安装。
6. 主代理审查并集成固定候选；Luna/xhigh 在 `work/worktrees/phase-1c-prep-p0-test` / `codex/phase-1c-prep-p0-test` 按Spec核验，只改 `tests/agent-integration/**` 与本阶段独立报告，执行候选包。私有文件只由Provider代码读，测试代理不读取/输出凭据。
7. 一次最小验证：独立工具/权限/次数护栏审查、本地取消夹具、两协议共4次请求，输出脱敏JSON。真实调用由测试负责人串行操作；主代理不重复调用。最终记录实际候选/脚本SHA、run_id、命令/退出码、预算累计。

## 验证与运行管理

使用仓库既有Python3.13.15和uv0.12.11工具链，可复用工具链缓存，虚拟环境独立于正在运行的主目录API。开发与测试只创建本批自有进程和忽略产物，不启动Kubernetes或正式Web/API，不改私有dev运行记录。

共享预算在主目录 ignored `work/phase1c-prep/p0-budget.json` 记录，真实调用账本由包实现持久化、锁定、拒绝超限；真实凭据同目录私有文件，权限0600，目录0700，不纳入Git。只记录检查窗口，不把静态开发时间冒充测试消耗；窗口内的等待/排查全部计入。

独立工作树无CodeGraph索引时rg/直接读取，不将主索引视作子树；主目录未集成业务代码，不重建主索引。交付完整集成分支，main服务与master不变，主入口导航可更新但不移动HEAD。未来0.5业务Spec/Plan仍待单独冻结。
