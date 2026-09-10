# Phase 1C 前置 P0 验收

- 状态：passed / P0 accepted。日期：2026-09-10。
- 本批只验收基线与受限模型/Harness适配，不代表正式Agent或0.5业务完成。
- 业务基准：381ae3a2205965ad6aab1ce787d490d2c02839f3；设计来源：8dcf7ecbc7fb9fe2ffe3df809bc621f3aaf1530a。
- 文档基线：cb7e4d1；开发交付：88fbe8e55d79fc185c14764bc6f0fc52f02eab4e。
- 被测集成候选：a84716c9d5c8f11b6bc3145c199743cac6af82b3；与开发交付的适配源码、pyproject及锁文件已核对一致。
- 独立执行：gpt-5.6-luna / xhigh；开发：gpt-5.6-sol / xhigh；主代理静态审查与最终证据复核。
- 测试脚本：14572c6f7dc127224bc5925e0f7efb5f4ebc965a；原独立报告：97d76749a382633ff6267f6cdbbecb2945cc15e4；计时澄清：fada0796432867c40d432704c3bc878cc0c027ed。
- run_id：p1cp0-20260910-a84716c。本文记录提交通过git log追溯，不预填自身SHA。

## 结果与证据

| 验收 | 结果 | 证据与界限 |
| --- | --- | --- |
| P0-01 基线 | passed | codex/phase-1c-prep从业务381ae3a建立，按明确清单集成设计Markdown；未集成旧spikes源码，正式API/前端/契约/迁移/生命周期未改；主HEAD及master保持不变 |
| P0-02 框架与工具 | passed | deepagents 0.7.13、langgraph 1.2.11、langchain 1.4.0、langchain-openai 1.6.2、langchain-anthropic 1.7.1固定并导入；实际编译工具仅wuji_synthetic_check；原生工厂ChatOpenAI/ChatAnthropic且retries=0 |
| P0-03 OpenAI Harness | passed | 受限Deep Agents经IPC Provider调用qwen-flash，2次请求完成工具往返；结束原因为tool_calls/stop，调用ID匹配 |
| P0-04 Anthropic客户端 | passed | 原生客户端经Provider进程完成2次同类往返，结束原因为tool_use/end_turn，未再运行第二套Harness |
| P0-05 取消等待 | passed | 独立延迟夹具通过真实ProviderSession._receive等待路径，cancelled/adapter_wait_ended/provider_process_cleaned均为true；不等同于Runtime停止 |

主代理亲自核对报告、4条持久attempt、工具ID、结束原因、用量与清理标志。OpenAI上游用量为输入430/输出24，Anthropic为输入354/输出26，合计834 Token；这是上游报告的用量和模型ID，不证明网关背后的实际模型身份或收费规则。4次均completed，无unknown/skip；每次输出上限256，真实请求不再追加。

密钥只由Provider子进程读取；CLI先清理Provider密钥环境并关闭遥测，IPC复用框架消息序列化。已检查私有文件权限0600、变更范围以及新增跟踪文件中没有长sk凭据模式；这不构成生产进程隔离的证明。源码权限与次数边界通过静态审查，正常往返与取消有实际执行证据，未扩展故障矩阵。

## 命令、环境与预算

- Python：开发worktree既有 `.venv/bin/python`，Python3.13.15；独立测试固定PYTHONPATH为候选包src并核对模块实际路径，无重复安装。
- 本地取消：`python -m wuji_agent_integration.probe --fixture-cancel`，exit0，shell wall约4.6秒。
- 真实验证：`python -m wuji_agent_integration.probe --credentials <private-path> --ledger <persistent-ledger> --report <artifact-report> --run-id p1cp0-20260910-a84716c --timeout-seconds 40`，exit0，shell wall约9.6秒。
- 离线报告检查：`python tests/agent-integration/check_p0_independent.py --source-root <candidate-package> --report <artifact-report> --ledger <persistent-ledger>`，exit0，约0.2秒。
- 上述命令路径说明与独立结果见 [独立报告](independent-test.md)；仅参数化记录本机私有路径，无凭据值。

**共享600秒预算累计保守记426秒，剩174秒；后续Phase1C前置批次沿用，不重置。真实模型4次额度已耗尽，不通过更换run_id或账本重新领取。**

| 窗口 | 秒数 | 依据 |
| --- | --- | --- |
| 依赖准备 | 94 | 93.5秒向上取整，含解释器定位、失败与安装；未替换已定依赖版本 |
| 开发本地检查与排查 | 34 | 含实际工具表、原生工厂、取消及失败报告检查 |
| 独立验证与协调 | 296 | 精确测试窗口UTC未采集；保守将候选提交06:52:25Z至首次独立报告提交06:57:21Z全计入，包含准备、等待和报告时间；不能把约15秒命令之和当完整窗口 |
| 主代理静态检查命令 | 2 | 基线/范围、私有文件权限和最终差异检查向上取整 |

独立子窗口180秒目标缺少完整计时证据，不能宣称该目标已验证；采用上述保守统计后仍在阶段共享600秒内。后续执行必须预先记录完整起止，不能只求命令时长和。计时澄清及后续纯文档整理未触发重跑。

忽略产物：本集成树 `artifacts/phase-1c-prep-p0/report.json`；主目录 `work/phase1c-prep/p0-calls.json` 和 `p0-budget.json`。未启动Kubernetes、正式Web/API或目标执行；自有验证Provider已清理，原主目录服务未操作。

## 修复与剩余限制

主代理审查要求修正启动失败清理、取消夹具绕开真实适配路径及失败不写报告，均在被测候选内完成。未知结果保留已预占次数；持久账本全局4次/每协议2次，不因新run_id恢复额度。

Deep Agents 0.7.13通过同名FilesystemMiddleware替换并清空其公开tools列表，关闭general-purpose子代理，且以实际编译工具表断言兜底；不能只依赖excluded_tools。该结论绑定本版本，升级时需定向复核，不由Prompt承担权限边界。

本次不验证长上下文压缩、持久恢复、多Agent、完整流式兼容、生产密钥/网络隔离、Runtime停止、价格与任务Token硬限额。下一批复用原生模型工厂与受限句柄，不将本次固定qwen-flash、256输出上限或4次检查额度变成产品永久默认值。

后续0.5仍需独立Spec/Plan：TenantAdmin组织模型配置、显式检查与组织级计量；独立草稿、任务范围确认及ConfigSnapshot；ready/历史queued兼容；新版交互评审后接正式前后端。Phase1A保持partial，master不前移。
