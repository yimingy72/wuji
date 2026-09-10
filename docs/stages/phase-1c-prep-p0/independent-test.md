# Phase 1C 前置 P0 独立测试记录

- 状态：`prepared`；尚未执行
- 测试工作树：`work/worktrees/phase-1c-prep-p0-test`
- 测试分支：`codex/phase-1c-prep-p0-test`
- 静态准备基准：`cb7e4d1`
- 被测集成 SHA：待主代理提供固定候选
- 测试脚本：`tests/agent-integration/check_p0_independent.py`
- 预算：依赖准备已耗 94 秒；当前窗口余 506 秒，后续开发本地检查继续计入共享 600 秒

本记录只准备独立核查入口，不代表 P0 任何验收项已通过。候选到位且主代理明确允许执行后，测试负责人使用开发树提供的既有 Python 3.13.15 venv，固定 `PYTHONPATH` 到候选适配包源码，仅运行一次最小流程。

## 待执行检查

| 检查 | 证据与边界 | 状态 |
| --- | --- | --- |
| P0-02 工厂与工具 | 源码检查原生 OpenAI/Anthropic 客户端、`max_retries=0`；报告核对实际工具集合只有 `wuji_synthetic_check` | 待运行 |
| P0-03 Harness 往返 | 固定 `qwen-flash`、OpenAI 兼容 2 次请求、工具 ID 与结果回传、输出上限 256 | 待运行 |
| P0-04 原生往返 | Anthropic 原生客户端 2 次请求，保留工具 ID、结束原因和用量；缺失用量保留 `unknown` | 待运行 |
| P0-05 取消清理 | 真实 `ProviderSession` 延迟等待取消后返回，Provider 子进程已清理 | 待运行 |
| 权限与次数护栏 | Provider 独立读取私有 JSON 路径；Harness 不读取或接收密钥；同一持久账本总计 4 次、每协议 2 次，失败/未知不重试 | 待运行 |

报告校验器只读脱敏报告、持久账本和候选源码，不导入适配包、不读取凭据、不启动进程、不联网。失败或未知结果保持不通过，不追加调用、不换模型、不执行第二轮 Harness/fallback 验证。

## 执行记录

待主代理提供候选 SHA、既有 venv/CLI、私有路径参数和执行许可后填写：`run_id`、业务候选 SHA、测试脚本 SHA、脱敏命令、退出码、耗时、OpenAI/Anthropic 实际次数、账本和报告路径、取消清理结果。凭据内容、会话凭据、原始敏感证据和本机配置不写入本记录。
