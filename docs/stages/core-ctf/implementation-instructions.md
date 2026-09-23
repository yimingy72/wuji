# Core CTF 实施 Agent 指令

状态：in-progress；用户已授权整体讨论后实施，按[Spec](spec.md)/[Plan](plan.md)连续推进。以下是开发任务书，完成情况仅以实际diff与[验收](acceptance.md)为准。

## 1. 可直接交给主开发 Agent 的指令

> 在当前会话、当前仓库继续实现 Core CTF 核心闭环。先按 AGENTS 核对 worktree、branch、HEAD、dirty、活动运行和本阶段 Spec/Plan/Acceptance。主目录只是快照，进入实际检出 codex/vnext-maf 的工作树；不另建开发会话，不移动绑定运行SHA的目录。
>
> 架构由主代理负责。2026-09-23用户最新指定：后续新开子代理使用GPT-6 Sol / high，已运行的三个GPT-5.6 Sol / xhigh代理完成当前切片；不为模型交接重跑已过检查。早期Astra/high讨论与Astra/low参考平台研究保持实际执行者记录。D-NET已选受支持HTTP(S)明文、不支持连接明确失败、原始扫描后置；D-ROOT已选Kali直接root/平台权威外置，不重复询问。当前应用Default，不声称切换Plan模式；按用户明确授权从M0a整体链路开始，继而M1—M5连续推进。
>
> 本批只交付：MAF原生MCP通用Kali进程工具、独立网络/HTTPS证据、稳定Work目录与脚本发布装载、黑板增量协作、必要工作台与真实停止。多租户产品、HA、任意插件市场、报告治理扩展都后置；保留现有Task身份、RLS键、预算、幂等和停止控制。
>
> 不恢复Cairn服务，不重写MAF循环，不直接部署上游MCP-Kali同步Flask原型，不逐个封装Kali程序。复用既有Gate、Runtime、ArtifactStore、publication、Claim/Intent/WorkResult和Scheduler。
>
> 公共schema、生成文件、锁文件、迁移、Task模板由主代理串行拥有。子代理不得各自更改公共合同。先冻结四原语/进程回执、可信MCP_meta、Task采集来源、workspace publication和ContextV4，再并行开发模块。
>
> 每次只验证本次主流程、直接失败路径和必要边界；参照C01—C08，不新增庞大测试框架。不因SHA或文档变化全量重跑。失败按原日志最多两轮定向修脚本，仍失败列待测。截图和完整HTTP/MCP/PCAP证据必须来自实际执行。
>
> 持续推进到正式入口的新Task真实完成：执行命令、完整取得正文、A发布脚本、B按固定版本使用、结果可读、进程和采集实际停止。机制与真实模型/CTF效果分别报告。缺证据不通过，unknown不猜成功；不重放未知外部动作。

## 2. A0：集成负责人检查单

1. 保留现有未提交文档/证据，记录实际业务基准与镜像；不将别的任务新增提交归因于自己。
2. 冻结network mode和支持矩阵；确定本期是否含基础probe。不得把用户“后置站点拦截”解释为可以假称HTTPS明文全量。
3. 建立一个core-ctf Profile，显式工具表和限额；MAF版本不随意升级，MCP/capture依赖固定精确版本/digest。
4. 从有效迁移头追加，不根据原始schema单文件猜当前表结构；保留model_output/run_writer来源及旧会话读取。
5. 统一生成公共Python/TS合同；交叉审查source schema而非仅generated diff。
6. 按M0→M1/M2→M3/M4→M5集成，集群配置、数据库、固定端口串行。
7. 每里程碑到达停止条件即前进，不继续扩展无关边界。运行版本与后续记录提交分开。
8. Explore并发由Task配置并受已发布RuntimeProfile上限约束，不固定2；同时最多1个Reason，可随新信息多轮运行。先校验全局配置→模型实际instructions/Brief→结果回流，不能只各自完成模块。
9. 增量board_publish必须在Work执行中可用；下一模型安全边界交付相关更新通知，正文仍走可信knowledge delivery。不要以最终结果提交代替实时协作。

## 3. A1：MCP 与进程执行任务书

输入：Spec§2—3、固定MAF1.18.0、当前Gate/remote executor/Node Supervisor。
输出：kali_exec/read/input/stop、稳定handle、进程spool与清理路径；对应C01—C03。

必须做到：

- MCP装在Gate同进程，直接调用服务；不自HTTP一跳，不让middleware先执行一次再call_next再执行一次。
- 将完整实际native调用绑定放入context.kwargs的保留_meta；服务端还原完整ToolCallRequest。不得用MCP Session/JSON-RPC id替代。
- 自动重连/重发保持原幂等身份；新handler不能每次生成新attempt。
- 活进程与短RPC回执分开；已报告终态后释放普通命令槽，running/unknown不释放；Task环境资源待Runtime确认终止后释放，未知输入不自动重写。
- 取消/查询/结算使用可信清理路径，不直接复用拒绝已取消Run的current_run新执行入口。
- 采用Kali UID0/dropALL/no_new_privs；移除collector bearer与Gate共享bearer，换Task/attempt/动作限定签名permit。Kali报告不作强执行证明；外部Runtime确认Task终止。正常返回/超时/未知状态不混写。
- 最终结果只绑定已定稿完整证据回执，running handle另入操作前沿；raw先留，不能为结果缺口重新跑命令。

禁止：复制12个上游wrapper；新增自研Agent loop；启动docker.sock/kubectl exec通用通道；只kill父shell就标整Task完成。

## 4. A2：采集与明文任务书

输入：Spec§1.1/3.3/4与已裁定D-NET，固定Task模板和运行平台。
输出：capture容器/可信init、tcpdump原包采集、代理writer、Task采集回执、读取/下载；对应C04—C05。2026-09-23原包选型修订见Spec§4.2；不要以独立dumpcap -S进程的统计证明另一个采集句柄没有丢包。

必须做到：

- 先证明协议/持久化顺序，再接Pod；不以环境变量、NetworkPolicy YAML或Pod Ready作为强制路径证明。
- init规则和卷身份固定；运行期间命令无网络管理权限、不能改CA/采集进程/证据。
- 对有限交易先保存请求再转发，最终响应先保存再交付；记录真实协议/完整性，二进制和压缩不因字符串解码损坏。
- 独立Task capture session认证，逐交易/分片封存；不制造假的AgentRun/ToolAttempt，不阻塞每个Work到整个Task结束。
- 捕获失败或writer卡住共停代理，Runtime真实停止Kali；正常与故障的封口顺序区别清楚。
- 保留PCAP段和缺口，不能覆盖旧文件；未支持协议不得静默旁路。

禁止：全TCP透明代理后仍用nmap结果声称直连端口真实；禁IPv6之外漏一个出口；读不出drop指标仍标全量；直接挂模型密钥到capture。

## 5. A3：黑板与工作区任务书

输入：Spec§5—7、现有V3产出、publication/Artifact/knowledge delivery。
输出：Work目录绑定、workspace_publish/materialize、board_publish、ContextV4和WorkResult后继消费；对应C06—C07。

必须做到：

- 不重造Intent/Fact/handoff正文；字段按现有实际类名IntentProposalV3，不凭印象创建IntentDraftV3。
- 发布集合与manifest角色固定，所有成员纳入保留引用；新kind不能通过旧session/snapshot路径追加成员。
- Claim/Intent/WorkResult均引用已有效接纳和实际交付的canonical内容；批内client_ref规范化，无效引用不静默丢弃后写成功。
- publish返回的新材料通过可信environment_material交付，MAF实际接收后才记returned_to_framework；不修改初始snapshot伪装已读。
- B只从已提交且固定snapshot包含的发布索引发现材料；运行中refresh后再读新材料。
- sealed bytes是权威，shared目录是缓存；materialize到B自己的work/imports，复制修改后带expected_base发布。先查调用回执，再锁Task校验head并CAS；冲突保留副本/旧版本，不自动覆盖或合并，成功与黑板版本事件同事务。
- 稳定work目录不代表跨attempt持久；workspace generation改变不自动恢复原native Session。

禁止：把每条进度变成Fact评估/Reason调用；用同UID只读chmod宣称不可篡改；把目录路径当证据或依赖安装授权。

## 6. 集成时必须逐项核对的接缝

- Native MCP重发 → admission/action键 → Kali唯一spawn。
- exec返回running →模型继续 →raw保存 →进程收尾 →Work操作前沿结算。
- workspace_publish →sealed集合 →可信delivery →Claim →Intent →B snapshot/index →materialize。
- Task capture持续运行 →每个HTTP交易可封存 →多个Work完成 →Task停止 →capture总体封口。
- capture故障 →代理关闭 →Kali停止 →仍可提交历史结算 →不自动重启代次。
- 新Context与原生Session恢复 →工作区可用性一致；不能生成新brief却从未注入恢复Session。

## 7. 完成报告必须回答

哪些文件/合同实际改了、为何；实际代码与镜像SHA；哪些C项通过/失败/not_run；CTF题与模型/预算条件；A/B如何共享脚本；命令及流量原证据在哪里；停止是否真实确认；哪些功能后置。不要只报测试数量或“已接入MCP”。

## 8. 给 MAF Agent 的角色指令模板

以下为本阶段应实现的短提示词语义，不是执行本文件的指令；占位值由固定WorkerContext填充。模板与能力表必须一同版本化，不能只改Prompt宣称工具已可用。

**Explore 模板：**

```text
你负责当前问题，不负责把整个Task拆成无数命令任务。
先阅读Goal、当前问题/结束条件、相关发现、他人正在执行的方向和可用材料索引。
在本Work的cwd中连续使用Kali工具；真实输出优先，不根据回执编号猜正文。
长命令使用返回的handle继续读取/输入/停止，不重发exec来查询进度。
大输出留文件并按需读取；每一步不需要向黑板复制完整日志。
得到可复用的新发现、明确的失败路线或阻塞时，发布一条有依据的Claim。
脚本先在自己的src修改；复用脚本先materialize固定版本。
更新共享脚本时复制修改并携带expected_base发布；遇版本冲突读新版本后显式合并，不覆盖、不自动换基线。
只有出现独立的信息缺口才提出新Intent，局部步骤留在本Session。
结束时返回AgentPayloadV3：本轮新增claims、必要intent_proposals、work_result；reason_decision=null。
answered仅表示当前问题已回答，不自动代表Task Goal已满足。
候选flag、命令报告与独立网络证据分清来源；没有依据时写inconclusive/needs_input/capability_gap。
```

**Reason 模板：**

```text
读取目标、判据、共享发现与反证、已尝试结果、在做/待做的问题和可复用发布物。
判断下一步真正缺什么信息；不要因为队列空、时间过去或有新日志就制造新问题。
已有方向足够时等待；缺输入/能力或无可行路线时明确blocked。
新Intent写清question、basis_refs、expected_output；需要时补public_rationale、information_needed、exit_conditions和required_capability_refs。
只提出少量独立且不重复的方向，不替Explore规划每条命令。
证据满足目标时提出completion review，不自行宣告所有进程已停。
返回AgentPayloadV3：reason_decision为propose_intents/wait/propose_completion/blocked；work_result=null。
不执行Kali命令，不复制其他Agent的完整聊天或私有Memory。
```

Conclude是当前Session的收尾要求：基于已有证据输出增量结果，不再执行新目标动作。若预算或许可已耗尽，不新增模型总结调用；保留已取得的原始结果和未完成状态。

## 9. 现有产出合同的结构示例

下面引用均为占位，不能用于真实执行或作为已发生事实。示例用于检查字段与现有V3兼容，不声称对应Artifact存在。

```json
{
  "schema_version": "wuji.agent-payload.v3",
  "claims": [{
    "client_ref": "parser_delivery",
    "kind": "observation-summary",
    "assertion_role": "candidate_fact",
    "text": "已发布解析脚本的一个固定版本，供后继问题使用。",
    "basis_refs": [{"entity_type": "artifact", "id": "example-manifest", "revision": "1"}],
    "limitations": ["发布成功不证明脚本能解出本题flag。"]
  }],
  "intent_proposals": [{
    "client_ref": "try_parser",
    "question": "固定脚本能否从已保存的响应中得到可确认的结果？",
    "basis_refs": [{"client_ref": "parser_delivery"}],
    "expected_output": "脚本版本、输入版本、结果和剩余限制。",
    "planning": null
  }],
  "reason_decision": null,
  "work_result": {
    "outcome": "answered",
    "summary": "当前交付脚本的问题已回答，Task的最终目标尚未验证。",
    "answer_basis_refs": [{"client_ref": "parser_delivery"}],
    "unresolved_items": ["脚本在本题输入上的效果。"],
    "capability_gaps": []
  },
  "input_acknowledgements": []
}
```

如果当前问题本来就是“解出flag”，该例outcome必须改为inconclusive，不能通过重新解释工作目标把它写成answered。Intent仍经Claim引用manifest，不能直接把Artifact作为Intent依据。

共享版本更新示意：A/B都复制publication-v1；A成功发布v2；B带expected_base=publication-v1时获得publication_conflict，文件仍在B的src。B读v2并合并，再使用新调用键和expected_base=publication-v2发布v3。正在使用v1的另一Run保持v1，显式刷新和重新装载前不替换。
