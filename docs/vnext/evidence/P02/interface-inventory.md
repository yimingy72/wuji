# P02 v2 接口资产梳理

日期：2026-09-13。权威 wire 来源：[`packages/contracts/openapi-v2.yaml`](../../../../packages/contracts/openapi-v2.yaml)。

P02 验证的是 schema、生成、认证和 JSON 组合边界。下表的“业务未实现”是预期状态：P03 及后续任务提供领域服务/路由，P02 不伪造业务结果。

| 方法与路径 | 资产责任 | 验证状态 |
| --- | --- | --- |
| `POST /api/v2/tasks` | TaskCreate → TaskView | 合同已验证；业务未实现 |
| `POST /api/v2/tasks/{task_id}/commands` | Task 生命周期命令 | 合同已验证；业务未实现 |
| `POST /api/v2/tasks/{task_id}/claims/proposals` | ClaimProposal 接纳 | 合同已验证；业务未实现 |
| `POST /api/v2/tasks/{task_id}/intents/proposals` | IntentProposal 接纳 | 合同已验证；业务未实现 |
| `POST /api/v2/work-items/{work_item_id}/commands` | Work hold/resume/cancel | 合同已验证；业务未实现 |
| `POST /api/v2/approvals/{approval_id}/decisions` | 固定审批决定 | 合同已验证；业务未实现 |
| `POST /api/v2/tasks/{task_id}/assessments` | 合格评估写入 | 合同与 model-only 拒绝已验证；业务未实现 |
| `GET /api/v2/tasks/{task_id}/topology` | 受权拓扑快照 | 合同已验证；业务未实现 |
| `GET /api/v2/views/{view_id}/events` | SSE view patch/reset | 合同已验证；业务未实现 |
| `GET /api/v2/tasks/{task_id}/snapshots` | 保存快照索引 | 合同已验证；业务未实现 |
| `GET /api/v2/tasks/{task_id}/records/{record_type}/{record_id}` | 固定 revision 记录 | 合同已验证；业务未实现 |
| `PUT /api/v2/tasks/{task_id}/layouts/{view_name}` | If-Match 布局更新 | 合同已验证；业务未实现 |
| `GET /api/v2/artifacts/{artifact_id}/content` | 受权不可变字节流 | 合同已验证；业务未实现 |
| `GET /api/v2/archives/{archive_id}` | 历史只读归档 | 合同已验证；业务未实现 |
| `POST /internal/v2/model/chat/completions` | Run 准入模型协议 | 合同已验证；业务未实现 |
| `POST /internal/v2/evidence` | 可信 CaptureEnvelope | 合同已验证；业务未实现 |
| `POST /internal/v2/results` | 可信 ResultEnvelope | 合同已验证；业务未实现 |
| `POST /internal/v2/dispatch/claims` | leader/capacity 派发领取 | 合同已验证；业务未实现 |
| `PUT /internal/v2/runs/{run_id}` | WorkerAssignment/StartReceipt | 合同已验证；业务未实现 |
| `POST /internal/v2/runs/{run_id}/control` | 控制接受与退出状态分离 | 合同已验证；业务未实现 |

实际利用/验证入口只有测试专用 `/api/v2/test/identity` 与 `/api/v2/test/claim`，由 `tests/vnext/conftest.py` 组合进真实 ASGI app，不存在于生产 OpenAPI，也不实现业务状态机。它们分别验证签名身份传播、strict JSON 和安全错误 envelope；完整交换见 [`http-reproduction.md`](http-reproduction.md)。
