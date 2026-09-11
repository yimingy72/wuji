# W1 验收记录

日期：2026-09-11；状态：**accepted：机制交付通过，自主模型效果待验收**。

业务候选：`f12a46fd904299960609c9856e1b988494cace49`；run_id：`p1a20260911t10152429fb64`；环境Docker Desktop / wuji-test / 4182。当前会话主代理负责架构、集成和实际联合/浏览器验收，明确范围的开发与定向检查使用gpt-6-astra/low子代理，不将这些称作独立全面测试。

## 实际交付

- 0008六表、不可变有限计划、VerificationRun/结果修订/Observation/EvidenceLink/CompletionReview；复用原ToolCall回执。
- http_request受控GET/HEAD/OPTIONS，双层目的地检查、敏感头剔除、响应截断/取消标记及元数据/正文双Artifact。
- 原生Cairn/Pi/LiteLLM和单Task双容器闭环，完成缺口持久反馈给Reason；不修改Core，不把总Goal自动标达成。
- 黑板/时间线/工作区下的评估视图与真实证据关联；保持创建交互及五主题。

## 验证及复用

| 检查 | 命令 / 实际结果 |
| --- | --- |
| 只读API | pytest tests/web-assessment/test_read_api.py：1项通过；临时PG/ASGI，真实项目/租户过滤、分页/精确Observation查找和双Artifact引用 |
| 规则与持久反馈 | pytest tests/web-assessment/test_evaluator.py：1项通过；实际execution角色、SQL及文件摘要校验，覆盖三判据、原提交重放、跨Task拒绝、追加纠错、两次无进展、新有效观察重置及unknown等待；HTTP/Runtime事实为明确模拟 |
| 原生阶段包装 | pytest tests/web-assessment/test_reason_adapter.py：6项通过；固定Cairn原生finally/租约释放，明确业务decision与普通失败分开 |
| 合成协议 | pytest tests/web-assessment/test_synthetic_model.py：最终5项通过；固定原生Bootstrap合同、在途Intent去重和压缩续接只读 |
| HTTP工具 | node --test tests/task-workers/http-observation.test.mjs：2项通过；本机真实子进程覆盖三站点路径、越界、大小截断、敏感头、重定向不跟随、SIGTERM保留片段 |
| 契约与构建 | contracts:check、API包、正式web及四镜像构建退出0。契约11条既有warning、web大chunk提示保留；相应日志见artifacts/phase-2-web-assessment。最后探针修正只重建相关运行镜像，不重跑旧全套 |
| 真实联合验收 | `.venv/bin/python tests/web-assessment/run_closed_web.py --run-file ABS/work/run/w1-final.json --record-out ABS/artifacts/phase-2-web-assessment/final.json --mode synthetic`：退出0；完整计数及真实镜像摘要见final.report.json |
| Codex浏览器 | 真实登录→工作区评估→catalog/a验证→结果修订→EvidenceLink→HTTP观察；三类状态、限制和两份产物入口清晰可读，截图browser-evidence.png；不复测主题矩阵 |

定向模块检查在候选冻结前对应内容上执行；最终联合实际测试上述f12a46f。创建/旧Scope/身份/原预算/通用停止等未变路径复用核心阶段的原SHA证据，不冒称本轮重新全测。

## 联合验收观测

Task：`6d050a5f-8e4b-4aa3-9618-b33d7221c6e1`，项目`8f81d77c-1890-53ee-a2ae-086097d0572a`。

- 9个AgentRun、1个Runtime attempt，三种原生阶段均实际运行；Task completed、资源清理completed。
- 有限计划4个资源：catalog/a confirmed；入口和catalog/b not_reproduced；account/view unassessed/blocked。Task assessment_outcome=partial，总Goal=unknown。
- 3次CompletionReview包含needs_followup；没有把业务缺口误当agent_result_incomplete。原生Cairn保持stopped，未伪造goal完成边。
- 7条EvidenceLink，逐项核验14份所引用Artifact的大小、SHA-256及元数据/正文绑定。
- 1次真实Pi原生compaction_end成功，1次原生custom-message工具表审计，之后6个真实读取工具开始/结束事件；保留task_read/assessment_read/evidence_read/graph_read等受限工具，没有默认bash/read/write/edit。
- 所有模型请求均是合成上游，经真实LiteLLM；没有新增公司模型费用。结果不代表真实模型自主推理或记忆质量。

## 实际失败与修正

1. 新Observation未改变覆盖状态时，旧snapshot短路遗漏progress_digest变化；按真实临时PG失败修正，相关单用例复测通过。
2. 固定Cairn Bootstrap执行返回必须同时有fact/complete；合成返回补齐，complete交平台评估。Bootstrap允许引用同Run原生conclude刚确认的Fact；不允许任意刷新扩大from集合。
3. 首轮候选9cbd68d的Task `6e8685e1-b056-40c9-ae68-e20b0e7b3100`已完成四资源/证据；脚本汇总SQL LIKE占位符错误修正后只读继续原Task，未重跑探索。
4. 首轮压缩探针在工具turn中报告高用量，Pi实际上在agent_end检查最后响应，且事件名为compaction_end。该项当轮未通过，没有伪造压缩证据。按固定源码修正为Bootstrap最终响应触发、原生CLI第二条只读消息续接，并以原生custom message记录工具表；在f12a46f仅重试这条联合入口后通过，不追加长故障矩阵。

## 限制与后续

- 自主模型效果pending，需另行明确已发布模型版本、公司单价及新增USD授权；本批只有合成推理协议。
- 仅入口及第一层最多10个同源获授权链接，方法为有限匿名HTTP配置观察；不是全站覆盖或完整漏洞影响验证。
- 未开放外部目标、任意Shell/MCP/代理、生产Pod出口隔离、全量流量截获或真实敏感证据分级。Artifact仍是开发PVC，客户端解码字节不是线包。
- 30秒超时和压缩响应解码分支已实现，未专项实测；本批已实际测大小截断和取消片段。长上下文质量、长断线及性能矩阵不在本轮。
- React Flow仍后置，Phase1A partial和既有未测清单不改写。

记录提交与被测代码SHA分开，不预写本文档自身SHA。交付前正常停止旧验收进程并保留库/PVC，再从记录提交生成当前版本运行文件；不手改SHA。交付记录为work/run/w1-delivery.json，实际入口/Task写入artifacts/phase-2-web-assessment/delivery.json。交付仅准备正常W1演示任务，不再重跑压缩或旧验收矩阵；主目录381ae3a、旧交付b79efa6及master保持。
