# 首用交付：合同映射与集成所有权

状态：implementation in-progress；2026-09-18 用户明确要求执行交付包，而非仅规划。源包 `wuji_subagent_delivery_20260918_v2.zip` 的 SHA256SUMS 全部校验通过。A1–A8 是本批分工，不替代 P00–P20 / E00–E08。

实际起点为 `codex/vnext-maf@b1ba8ec6a7205230f6ea2067e273c82c447d977b`。应用附着工作树停在 `c9ec371`，不是本批实现来源。原工作树四个未跟踪 E08 诊断目录原样保留。无 CodeGraph 索引，定位依据为当前源码与 Git。历史验收不因本批重新标记通过。

| 合同 | 基线事实 | 本批映射与兼容 | 所有者 |
| --- | --- | --- | --- |
| C01 create | `POST /api/v2/tasks` → `TaskService.create` → `vnext.create_task`；ready/pause，不启动 | 保留路由/TaskCreate/TaskView；增加可选 entry_points，校验 scheme/host/port，保留 path/query；旧客户端继续派生起点 | A2 |
| C01a options | 未有正式目录路由；已有 tenant published_profile | `GET /api/v2/projects/{project_id}/task-options`，只读授权白名单字段 | A2 |
| C01b list/get | 只有创建回执，没有正式目录 | `GET /api/v2/tasks?project_id&limit&cursor`、`GET /api/v2/tasks/{task_id}`；TaskList/TaskView，逐页重新授权 | A2 |
| C02 start | 公开 TaskCommand 与 owner 四阶段脚本分离 | 公开 start 持久接纳；后台 prepare/activate/wire/capability；activate 调领域 Control；固定操作身份，不在 HTTP 内起 owner 脚本 | A2/A7 |
| C02a launch | 现有脚本回执不构成持久产品查询 | `GET /api/v2/tasks/{task_id}/launch`；新的 launch 作业只表达命令执行进度 | A2 |
| C03 readiness | 已有 owner preflight，不能供浏览器直接执行 | `GET /api/v2/tasks/{task_id}/readiness`；无目标/模型调用，实测未知保持 unknown | A2/A7 |
| C04 BFF | `services/wuji-web-gateway/main.py` 固定身份与 Task | 明确 local_single_operator 身份，严格路由/CSRF/限额，受权多 Task 与 view/session 绑定 | A3 |
| C05 material | 内部 material 只支持 text/*；HTTP exchange 是 vendor JSON | 原端点 `?representation=wuji.model-material.v2` 显式选择；无参数保留 v1；源/表示分别摘要，Worker/Profile 显式钉版本 | A5 |
| C06 model | 现有 MAF → ModelGate → LiteLLM 链 | 受信 alias `wuji-deepseek-observe-v1` → `deepseek-flash`，non-thinking；参数映射在 LiteLLM，provider Key 仅网关 | A6 |

共享 OpenAPI、生成 Python/TypeScript、迁移编号/注册与锁文件仅由 A0 合并。TaskList 固定 `items: TaskView[]` 与 `next_cursor: string|null`；其他新增 DTO 在同一 OpenAPI 冻结，不由消费者复制 wire。迁移基线 `vnext_0028_p06_platform_run_settlement`，为持久启动预留 0029；历史迁移不改写。

基线 OpenAPI SHA256：`311492bbe49e79d92150930eb183b7f656d3de5b126804a34152e12fbc07453e`。MAF lock：`6cf936d2efcdf7cdd4cba7d7758c73ca37879c7e89b38da0318c81ea6375df01`；pnpm lock：`f6d22f211040da5b4e916d4942f8f07e236ad2499fb53d176ad3d76762c6bdef`。

各角色在 `codex/first-use-aN` 独立工作树实现。用户指定子代理 `gpt-5.6-luna/xhigh`；并发上限六个，A3/A4 排队，不伪报启动。A8 不写生产实现，在固定集成版本独立复核。DG0代码、DG1机制、DG2真实模型、DG3现场分别报告。

用户已选择 DeepSeek 并提供凭据；记录与任务只保存 SecretRef，不再索要 Key。优先复用有效预算、数据许可与隔离部署批准。尚未找到的额度/现场信息保持缺项；自建无害开发验证持续进行。
