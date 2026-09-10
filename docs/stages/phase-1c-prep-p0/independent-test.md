# Phase 1C 前置 P0 独立测试记录

- 状态：`executed`；一次有界独立验证完成，阶段验收仍由主代理复核
- 测试工作树：`work/worktrees/phase-1c-prep-p0-test`
- 测试分支：`codex/phase-1c-prep-p0-test`
- 静态准备基准：`cb7e4d1`
- 被测集成 SHA：`a84716c9d5c8f11b6bc3145c199743cac6af82b3`
- 测试脚本：`tests/agent-integration/check_p0_independent.py`，提交 `14572c6f7dc127224bc5925e0f7efb5f4ebc965a`
- 运行：`p1cp0-20260910-a84716c`
- 预算：依赖准备耗时 128 秒；本独立窗口约 15 秒（取消夹具 shell wall 4.6 秒、真实 CLI shell wall 9.6 秒、离线报告核验约 0.2 秒），未达到 180 秒上限；阶段共享预算余约 457 秒，后续开发检查继续计入

本记录绑定固定候选完成一次最小独立核查，不代表生产隔离或后续业务验收已通过。测试使用开发树提供的既有 Python 3.13.15 venv，固定 `PYTHONPATH` 到候选适配包源码；模块 `__file__` 已核对为候选包下的 `wuji_agent_integration/__init__.py`。未读取凭据内容。

## 独立检查结果

| 检查 | 证据与边界 | 状态 |
| --- | --- | --- |
| P0-02 工厂与工具 | 源码检查原生 OpenAI/Anthropic 客户端、`max_retries=0`；报告核对实际工具集合只有 `wuji_synthetic_check` | `passed` |
| P0-03 Harness 往返 | 固定 `qwen-flash`、OpenAI 兼容 2 次请求、工具 ID 与结果回传、输出上限 256 | `passed` |
| P0-04 原生往返 | Anthropic 原生客户端 2 次请求，保留工具 ID、结束原因和用量；缺失用量保留 `unknown` | `passed` |
| P0-05 取消清理 | 真实 `ProviderSession` 延迟等待取消后返回，Provider 子进程已清理 | `passed` |
| 权限与次数护栏 | Provider 独立读取私有 JSON 路径；Harness 不读取或接收密钥；同一持久账本总计 4 次、每协议 2 次，失败/未知不重试 | `passed` |

报告校验器只读脱敏报告、持久账本和候选源码，不导入适配包、不读取凭据、不启动进程、不联网。失败或未知结果保持不通过，不追加调用、不换模型、不执行第二轮 Harness/fallback 验证。本轮没有失败或未知尝试。

## 执行记录

- 无网络静态护栏：退出码 `0`。源码与模块路径核对通过，实际工具集合、原生工厂、两处 `max_retries=0`、共享/协议次数限制均满足；未做 model discovery 或连通预热。
- 本地取消命令：`PYTHONPATH=<candidate>/packages/agent-integration/src <existing-venv>/bin/python -m wuji_agent_integration.probe --fixture-cancel`；退出码 `0`；shell wall `4.6s`，夹具自身耗时 `1.144345s`；`cancelled=true`、`adapter_wait_ended=true`、`provider_process_cleaned=true`。
- 真实命令：`PYTHONPATH=<candidate>/packages/agent-integration/src <existing-venv>/bin/python -m wuji_agent_integration.probe --credentials <private-path> --ledger <shared-ledger> --report <candidate>/artifacts/phase-1c-prep-p0/report.json --run-id p1cp0-20260910-a84716c --timeout-seconds 40`；退出码 `0`；shell wall `9.6s`；实际请求恰为 4 次。
- OpenAI 兼容 Harness：2 次，实际模型均为 `qwen-flash`；结束原因为 `tool_calls` / `stop`；用量为 `(195,18,213)` / `(235,6,241)`（输入/输出/总计）。工具 `wuji_synthetic_check` 的调用 ID 与结果回传匹配，最终文本为 `WUJI_GATEWAY_OK`。
- Anthropic 原生客户端：2 次，实际模型均为 `qwen-flash`；结束原因为 `tool_use` / `end_turn`；用量为 `(157,18,175)` / `(197,8,205)`（输入/输出/总计）。工具调用 ID 与结果回传匹配。
- 持久账本核对：本 run 4 条记录，OpenAI 2 条、Anthropic 2 条，序号各为 1/2，均 `completed`；限制为共享 4、每协议 2、SDK retries 0、输出 256。报告记录 `provider_secrets_present_in_harness=false`、`external_tracing_enabled=false`，两 Provider 清理标志均为 true。
- 离线检查命令：`<existing-venv>/bin/python tests/agent-integration/check_p0_independent.py --source-root <candidate>/packages/agent-integration/src/wuji_agent_integration --report <candidate>/artifacts/phase-1c-prep-p0/report.json --ledger <shared-ledger>`；退出码 `0`；检查器未启动模型或进程。
- 报告与账本均保持脱敏；未验证生产隔离、Runtime 停止确认、长上下文摘要、持久恢复、多 Agent 或完整流式协议兼容性。凭据内容、会话凭据、原始敏感证据和本机配置不写入本记录。
