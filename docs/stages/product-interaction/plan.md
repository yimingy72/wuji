# 产品交互原型 Plan

状态：approved / in-progress。用户确认产品方案，当前执行模式仅进行原型与元刃静态复核。

1. 主代理：记录确认状态及本 Spec/Plan；复核元刃文档，补后端差异与证据边界，保持业务工作区 HEAD 和运行服务不动。
2. 开发代理 `gpt-5.6-sol / xhigh`：独立分支 `codex/product-interaction-prototype`、worktree `work/worktrees/product-interaction-prototype`；只修改 `spikes/frontend/src/**` 和必要的 `spikes/frontend/index.html`，复用现有依赖、主题与 Vite 工程。不修改正式 apps、契约、迁移、manifest、锁文件、根命令或本阶段文档。不拆子代理。
3. 子代理先读产品方案、Spec、PRODUCT/DESIGN 与 Ant Design skill，查询实际组件 API。实现两条原型路径，允许重构该隔离工作树中的历史原型，不改变正式工作区。
4. 检查预算：全部工作共享 600 秒。开发代理安装/构建/lint/脚本排查累计最多 180 秒，记录实际耗时；主代理使用剩余预算做一次浏览器走查及必要修复，不重复平台/API/旧原型回归。同类脚本问题最多两轮。
5. 依赖若需准备，使用已有锁文件冻结安装；不引入新依赖。验证命令：`pnpm --dir spikes/frontend build`，`antd lint <changed-path> --format json`；只针对原型。
6. 主代理审核并合入文档/原型分支，按实际候选提交记录构建与浏览器证据。独立原型本地入口拟用 `127.0.0.1:4185`，严格占端口；若冲突先报告真实占用，不停止他人进程。
7. 启动示例：在原型工作树使用 `pnpm --dir spikes/frontend exec vite --host 127.0.0.1 --port 4185 --strictPort`。不调用现有平台生命周期命令。

交付：提交 SHA、改动范围、检查命令/耗时/退出码、原型入口、已知限制。业务后端必须等原型确认后进入具体 Phase 1C 规划；元刃复核不授权重写 Harness 或提前部署 Runtime。

2026-09-10 用户补充 Cairn 黑板要求：主代理核对官方协议与当前源码，追加黑板架构建议；开发代理在完整 Agent 原型中加入最小 Fact/Intent/Hint 关系视图与模拟 Hint 输入，继续原文件范围及同一 600 秒预算，不另启全图编辑项目。角色显示为能力配置，不能把规划写死为多角色线性流水线。
