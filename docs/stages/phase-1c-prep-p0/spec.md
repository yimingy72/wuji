# Phase 1C 前置 P0：基线与框架适配 Spec

- 状态：approved；2026-09-10。
- 批准依据：用户明确要求 IMPLEMENT 本批完整计划，应用已进入执行模式。
- 业务基准：381ae3a；设计来源：8dcf7ec；仅按清单复制 Markdown，不集成旧原型源码。

## 目标与范围

交付可继续开发的 codex/phase-1c-prep 集成基线、独立可复用 Python 模型客户端与 Harness 适配验证包、真实能力与限制记录。API 保持0.4.0；正式任务、数据库、Runtime、黑板、目标请求、流量控制不变。后续任务模型预算选 Token 上限，金额限制不开放。

原生 langchain-openai / langchain-anthropic 管协议；受限 Deep Agents 管循环，LangGraph 管编排。候选版本为 deepagents 0.7.13、langgraph 1.2.11、langchain 1.4.0、langchain-openai 1.6.2、langchain-anthropic 1.7.1。传递依赖统一锁定，不兼容时记录阻塞，不换框架或静默升级。

## 输入、边界与输出

- 模型配置只含协议、base_url、模型ID、超时、输出上限；工厂返回原生 BaseChatModel。真实验证固定 qwen-flash、两个既有已授权兼容网关，禁止自行发现其他模型或换模型重试。
- Provider 独立进程读取本机私有JSON文件的 api_key；Harness 进程不得读取文件内容、携带上游密钥环境变量或收到密钥。IPC 仅传配置、消息、工具定义和框架序列化结果，薄 BaseChatModel 适配不实现新循环。
- 只开放一个确定性的合成工具。禁用默认文件/Shell/子代理、自动技能/记忆加载与外部遥测，核查实际编译工具清单。工具不读文件、不联网、不访问目标。
- 每次上游实际尝试发送前原子记录到同一持久调用账本，计入最多4次；重复执行验证入口不重置计数。全部SDK retries=0，输出最多256 Token，输入仅短合成材料；不明结果也消耗次数且不自动重发。
- 两次OpenAI兼容请求完成一次 Deep Agents 工具往返，两次Anthropic兼容请求完成原生客户端的同类往返。禁止第二轮真实Harness或fallback验证。
- 工具调用ID、实际模型标识、结束原因与上游用量保留；未提供字段记录unknown，不猜测真实底层模型或按零计费。账本用途为组织配置检查，无虚构Task归属。
- 本地延迟夹具验证取消等待并清理自有子进程；不声称生产隔离、Runtime停止、长上下文压缩、持久恢复、多Agent或完整流式协议已通过。

## 验收

| ID | 通过标准 |
| --- | --- |
| P0-01 | 新集成基线有正式根规则/完整索引，仅集成指定文档，main HEAD/master及服务不变 |
| P0-02 | 固定依赖成功导入；工厂使用原生客户端；实际工具集合仅合成工具 |
| P0-03 | OpenAI兼容 qwen-flash 经受限 Harness 完成工具调用与结果回传，调用归属和用量可核对 |
| P0-04 | Anthropic兼容原生客户端完成同类往返，保留工具ID/结束/用量字段 |
| P0-05 | 本地延迟夹具取消后适配等待结束，自有Provider进程已清理 |

本批加入 Phase 1C 前置共享600秒预算，依赖准备、等待、检查、排查/复跑计入，不因提交、代理或后续批次重置；达到上限清理并记录。失败同类最多两轮，不追加真实调用。Deep Agents失败只给create_agent + SummarizationMiddleware适用判断，不启动替代方案验证。
