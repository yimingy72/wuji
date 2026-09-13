# C0 源码与运行绑定

## Git 关系

- 测试基线/代码提交父级：`890b54064f370c6e9ace2bc5d92cce2a86a1eefc`
- C0 SOL 代码提交：`d2beac6980aab7959367299f91e4dd2558de9b59`
- Remote 核心原提交：`3bd7d8ab0137c82ba99eee9188316c59b123bcfb`，本批 SOL 未修改其三个生产文件。
- 0017 migration 提交：`890b54064f370c6e9ace2bc5d92cce2a86a1eefc`，本批 SOL 未修改迁移源码。

`d2beac6` 的文件与 Git blob：

| 文件 | 状态 | blob |
| --- | --- | --- |
| `packages/task-runtime/src/wuji_task_runtime/controller.py` | modified | `b5d108fa420c07d5b6f42b8b716e372118e9a067` |
| `packages/task-runtime/src/wuji_task_runtime/manifest.py` | modified | `3d85839c0258209d692a17a6f14e0c1a519baf30` |
| `packages/task-runtime/src/wuji_task_runtime/models.py` | modified | `b720bc6186db1eb013a31ca3facb110000cc4c2c` |
| `packages/wuji-core/src/wuji_core/execution/pod_runtime.py` | modified | `1ba249ff290287a2641ca784fc60f6285d2dd67e` |
| `tests/vnext/support/c0.py` | added | `6536e8d3001bf8b528a8495158c9fdca5459e6d2` |
| `tests/vnext/test_pod_runtime.py` | added | `e72ee3665d3f8f35f40709fb7e9ad605a2a4089f` |
| `tests/vnext/test_remote_workspace.py` | added | `8c664410679fcd62bf02b451a7768653fb44f7c4` |

生产修复增加显式 `TaskRuntimeConfig.kali_receipts_enabled`。默认 `False` 时不改变旧 Pod 模板输出；vNext `VNextPodRuntime` 要求 `True`。启用后资源名为 `resource_names["kali_receipts"]`，PVC 仅挂 Kali `/var/lib/wuji/kali-receipts`，不挂 agent/Gate；Kali UID 为 10002，Pod fsGroup 为 10000。该资源进入 template digest、资源归属预检与 template matching。

`receiver_id` 没有拆分或改值。C2 已确认同一 Task Pod/runtime_attempt 的 Node Run receiver、`ExecutorRegistration.receiver_id`、`PodReceiverRegistration.receiver_id` 与 `ExecutorDeploymentBinding.receiver_id` 使用同一受管配置值；gate/collector/receiver subject 与网络端口仍分别约束。

## 实际运行顺序与准确限制

1. 两次 collection 依次暴露 maf-worker venv 缺 `wuji_task_runtime`、加入源码路径后缺其锁定的 `kubernetes` 依赖。随后改用已有根 `task-runtime` dependency group；两次输出均作为环境历史保留，不计产品失败。
2. 首轮目标集合运行于 `890b540` 加未提交 C0 diff。输出顺序为纯 wire PASS、6 个 Remote TLS FAIL、两个 Pod PASS。TLS FAIL 均发生在证书验证的 `Missing Authority Key Identifier`，尚未到业务 HTTP。
3. 测试 CA 增加 SKI/AKI，保持 `CERT_REQUIRED`、hostname 校验、SAN 与 TLS 1.2 下限；同时修正一个生成 RootModel 的测试断言。Remote 文件最终为 7 passed / 14.81s。
4. Remote 最终运行后、提交前，从 `tests/vnext/support/c0.py` 删除了未引用的 `with_response_mutation` 辅助函数。该函数从未被测试或生产入口调用；没有为此重跑。
5. 默认未启用 receipts 配置的模板兼容检查在最终源码上为 1 passed / 0.01s。随后将七个 owned 文件提交为 `d2beac6`。

运行时未执行 `git write-tree`，因此没有准确的未提交树 SHA。不能把 `d2beac6` 说成逐字节等同于 Remote 最终运行树；差异限上述未引用辅助函数删除。Pod 测试不导入 `support/c0.py`，其生产文件在通过后没有变化。
