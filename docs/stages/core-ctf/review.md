# 设计研究、交叉审查与裁定记录

日期：2026-09-22。性质：源码/方案审查，不是运行、安全测试或第三方认证。主代理负责最终架构；按用户最新要求，三项最终专题及交叉复审均由 **GPT-6 Astra / high** 执行。早期low研究材料只作检索输入，不冒称high执行。

工作树基准 `3682edae86ddd438892e0961803aae3eb6fa6bb2`。未改业务代码、未安装MCP/代理、未请求目标、未抓用户流量。详细研究过程保留在忽略目录 `work/research/core-ctf-plan/`；本页保存可随仓库交付的关键事实和裁定。

## 1. Kali MCP 实际工具及固定来源

固定上游：[MCP-Kali-Server@00154c053845b2ec4c3eef49ad09dd9bb2d3b7aa](https://github.com/Wh0am123/MCP-Kali-Server/tree/00154c053845b2ec4c3eef49ad09dd9bb2d3b7aa)，与[Kali官方包页面](https://www.kali.org/tools/mcp-kali-server/)的短SHA对应。已读取client.py/server.py原文并核对完整提交。

| MCP工具 | 实际用途 |
| --- | --- |
| nmap_scan | nmap参数包装 |
| gobuster_scan | gobuster参数包装 |
| dirb_scan | dirb参数包装 |
| nikto_scan | nikto参数包装 |
| sqlmap_scan | sqlmap参数包装 |
| metasploit_run | 模块及options包装 |
| hydra_attack | 目标/服务/账号及字典参数包装 |
| john_crack | hash/wordlist/format包装 |
| wpscan_analyze | URL及附加参数包装 |
| enum4linux_scan | 目标及附加参数包装 |
| server_health | 服务检查 |
| execute_command | 接受command字符串的通用shell |

结论不是“没通用工具”：它确实有execute_command。但client是MCP桥到同步requests/Flask API；没有稳定长进程handle、增量读取、stdin和取消合同。server硬超时实际180秒，且stdout/stderr线程join没有完整总时限；只结束直接子进程，输出无界累积。超时有输出可标success，不能当平台执行事实。两个名字带MCP的Flask路由在此提交仍是pass。

源码：[client.py](https://github.com/Wh0am123/MCP-Kali-Server/blob/00154c053845b2ec4c3eef49ad09dd9bb2d3b7aa/client.py)、[server.py](https://github.com/Wh0am123/MCP-Kali-Server/blob/00154c053845b2ec4c3eef49ad09dd9bb2d3b7aa/server.py)。固定文件SHA256分别为 `10f8b5b0332bf98cbeb0783efd0049b4c7bfdb222da45577b5bf1a93fde0f74c`、`4468f08faf247abe546432a14f8db226f314b952f5a6dd7b1c6101346b31be7a`。

裁定：不原样集成上游原型，不移植十个程序wrapper；复用MAF原生MCP与Wuji既有准入/记录，新增少量通用进程语义。

## 2. MAF 接缝的独立核对

MAF core1.18.0 wheel与当前uv.lock SHA256一致：`75f2fac5eed229c62f0665630cf1478eb45204bde41200a4c94dab57d441cc84`。_mcp.py、_tools.py、_middleware.py与wheel字节核对一致。

- 原生MCP发现的工具进入FunctionMiddleware，因此不需要重写工具循环。
- native call_id/occurrence在context.metadata；MCP caller发送的是context.kwargs['_meta']。平台必须显式桥接，MCP不会自动带上完整MAF身份。
- 连接关闭/session terminated可能触发重连后重发tools/call，所以必须复用稳定业务操作键和执行端去重。
- server tools/list meta可能覆盖runtime meta，保留平台命名空间须校验拒绝。
- 当前安装未包含mcp运行依赖；仅有类定义不能证明已可运行。

依赖候选已查公开发行元数据：mcp1.24.0满足MAF声明的最低范围，mitmproxy12.2.3要求Python≥3.12；这只是候选可获取性，不是二者与当前镜像的兼容通过。M0须固定最终版本/digest并实测直接接缝，不自动升级MAF。

本轮M0补核：针对当前Worker环境执行`uv pip install --dry-run ... mcp==1.24.0`能解析依赖，未安装、未改变环境，仍不算原生调用通过。mitmproxy12.2.3发行元数据限制cryptography<=48.1，而wuji-core固定50.0.1；capture必须使用已计划的独立镜像/依赖环境，通过HTTP采集入口交付，不把mitmproxy塞进MAF/平台虚拟环境或降级平台加密库。[发行元数据](https://pypi.org/pypi/mitmproxy/12.2.3/json)

M0采集接缝补核：已在ignored的`work/core-ctf-capture-env`独立安装mitmproxy12.2.3，确认Python3.13.15可启动；平台/MAF环境未改。固定版本的非流式`request`钩子发生在请求发出前，`response`钩子发生在最终响应发出前；`requestheaders`可在代理处理Expect之前拒绝，HTTP/1上游响应头会进入`responseheaders`。因此首版可用这些公开钩子实现有限正文持久化屏障及1xx拒绝，仍需真实HTTP/TLS检查，源码顺序不算交易验收。尤其addon普通异常会被框架记录后吞掉：writer错误必须显式kill当前flow并使capture失败关断，不能只抛异常后继续转发。依据：[固定版本HTTP层](https://github.com/mitmproxy/mitmproxy/blob/v12.2.3/mitmproxy/proxy/layers/http/__init__.py)、[HTTP/1响应处理](https://github.com/mitmproxy/mitmproxy/blob/v12.2.3/mitmproxy/proxy/layers/http/_http1.py)、[addon异常处理](https://github.com/mitmproxy/mitmproxy/blob/v12.2.3/mitmproxy/addonmanager.py)。HTTP/2尚未验证，不因库支持就自动列入首版发布能力。

2026-09-23原包选型修订：dumpcap的`-S`进入单独的统计循环并另开pcap句柄，不能与写文件采集的丢包计数混用；已读取的上游源码还在多文件模式跳过末尾ISB写入，在线更新pcap_stats代码被禁用。因此“分段dumpcap加-S就有可靠实时drop指标”的假设不成立。首版改为固定Linux tcpdump进程写递增PCAP分段，通过SIGUSR1取得该采集句柄统计、SIGUSR2请求flush；不使用-W覆盖旧分段，不以外部统计进程补造零drop。tshark继续离线读取，HTTPS明文仍由mitmproxy采集，用户的数据保留要求不变。固定包/镜像及信号实际行为尚待M2验证，不把上游master当已安装版本；不fork上游抓包器。依据：[dumpcap源码](https://github.com/wireshark/wireshark/blob/master/dumpcap.c)、[dumpcap手册](https://www.wireshark.org/docs/man-pages/dumpcap.html)、[tcpdump4.99.5手册源码](https://github.com/the-tcpdump-group/tcpdump/blob/tcpdump-4.99.5/tcpdump.1.in)。下文dumpcap候选属于修订前研究记录，以本条和Spec§4.2为当前实施方向。

2026-09-23 HTTP/1 trailers实施补核：固定mitmproxy12.2.3在同批输入包含headers、chunked body与trailers时，可在公开HTTPFlow钩子前抛出未实现错误。首版保留普通有限chunked支持；可见Trailer/实际trailers按交易拒绝，前置框架崩溃则由监督进程关断代理并记录采集窗口incomplete/failed与原包，不虚构逐交换明文。避免为未支持协议增加前置解析器或fork上游；实际日志与通过范围由采集验收记录保留。

## 3. Cairn 字段与调度：实际可借鉴内容

固定提交 `8e7e0ea67552383851dfcabfba0c4e9c8d007878`。下载的调度/tasks文件与仓库旧upstream-hashes.json逐项一致。

| Cairn输入/产出 | Wuji已有对应 | 本期强化 |
| --- | --- | --- |
| Origin/Goal/Hints | Task Goal、用户输入与提示 | 不再新增永久Bootstrap角色 |
| Graph YAML | snapshot + brief + index +按需材料 | 新Agent拿确定版本、工作环境与共享资产索引 |
| Current Intent及方向说明 | IntentProposalV3.question/expected_output/planning | 子问题持续在同Session，不拆成每命令一项 |
| Explore增量description | ClaimProposal + WorkResult | 中途发布、证据引用、负结果和限制 |
| Reason from[] +方向/完成/noop | basis_refs + reason_decision | 保留等待/无进展，不强迫空队列编新题 |
| 文件路径写入description | 现有Artifact与目录引用 | 增publication版本、manifest、依赖和可复现装载 |

Cairn调度是active项目轮询、容量限制、初次工作、Fact/Hint增长或待办从有到零触发Reason，再派未认领Intent。实现还包含认领、心跳、超时收尾、失败冷却；Worker按priority/运行数及随机平局选择，Intent偏最新。Wuji可借鉴决策规则，但不能把进程内Future直接当持久账本。

来源：[提示词](https://github.com/oritera/Cairn/tree/8e7e0ea67552383851dfcabfba0c4e9c8d007878/cairn/src/cairn/dispatcher/prompts/default)、[调度](https://github.com/oritera/Cairn/blob/8e7e0ea67552383851dfcabfba0c4e9c8d007878/cairn/src/cairn/dispatcher/scheduler/loop.py)、[Worker选择](https://github.com/oritera/Cairn/blob/8e7e0ea67552383851dfcabfba0c4e9c8d007878/cairn/src/cairn/dispatcher/scheduler/worker_select.py)。

## 4. 交叉讨论中修正的接缝

| 发现 | 最终写入Spec的处理 |
| --- | --- |
| MCP接入可能双执行/重发 | 唯一Gate入口、唯一Kali spawn、原业务键复用；不MCP再HTTP调用自己 |
| 现同步工具必须complete才返回 | ProcessReply与最终证据回执分开；running handle不塞最终refs |
| 已取消Run不能走current_run新动作准入停止 | 清理许可单独处理stop/query/settle |
| stdout父进程退出不代表后代全停 | leader/job分开，未知进程Task级收敛，Kali PID namespace终止兜底 |
| capture按ToolAttempt绑会伪造身份、阻塞Work | 独立Task capture session，逐交易/分片封存，Task最后总封口 |
| 初始Artifact schema不是有效迁移后结构 | 保留model_output/run_writer分支，只对capture来源增加二选一 |
| capture活着不代表writer可用 | 有界存储/采集健康检查，故障共停与Runtime终止 |
| 任意shell可读取同UID服务秘密 | 形成两种明确执行信任选项，见§6；不假称单改UID即可 |
| shared同UID只读chmod不等于不可变 | sealed Artifact为权威；工作副本修改，新版本CAS；缓存与权威分开 |
| publication原入口可追加成员 | 新kind专用权限、成员冻结、聚合ACL、固定manifest角色 |
| 发布物不在初始snapshot | 可信当前Run材料交付；MAF实际收到后才标已读 |
| WorkResult批内引用与后继消费未闭合 | 规范化client_ref、保留invalid_refs、有效结果进入brief |
| native恢复messages=None不会注入新brief | workspace generation变更不自动继续旧Session |
| 编辑共享脚本会覆盖别人 | 复制固定版本、CAS发布、冲突保留工作副本、显式合并、旧运行不热更新 |

以上是设计修改，不是代码已修复或运行通过。

## 5. 抓包与明文的真实取舍

选型建议为dumpcap分段原包 + mitmproxy有限HTTP明文 +独立命令输出。只设代理环境变量不能覆盖任意程序；全TCP透明代理可能污染nmap connect扫描结果；被动抓包不能在任何故障下承诺零漏。严格明文需要受支持协议与可验证采集路径。

capture同Task网络、独立PID/卷，agent/kali不持采集CA私钥或证据写权限。普通container+Never，PID1共停子进程，现有Controller核对Task停止；不为此新建集群controller。原包、协议实体字节、解压显示和模型摘要分层保留。

用户已选择D-NET严格受支持HTTP(S)明文，不能采集的连接明确失败，原始扫描后置；首版不加入基础probe。此前两模式/原始网络缺口仅保留为曾讨论的选项，不实施。

来源：[mitmproxy模式](https://docs.mitmproxy.org/stable/concepts/modes/)、[协议范围](https://docs.mitmproxy.org/stable/concepts/protocols/)、[证书](https://docs.mitmproxy.org/stable/concepts/certificates/)、[dumpcap](https://www.wireshark.org/docs/man-pages/dumpcap.html)、[Nmap connect](https://nmap.org/book/scan-methods-connect-scan.html)、[Kubernetes网络策略](https://kubernetes.io/docs/concepts/services-networking/network-policies/)。

## 6. 用户 root 问题的追加裁定材料

root指容器Linux UID0，平台凭据是服务间token/证书，回执是执行记录；不是靶场账号。root不自动等于宿主权限，是否能做raw扫描取决于capabilities和网络路径。

| 选项 | 可以保留的保证 | 代价/变化 |
| --- | --- | --- |
| A：Kali命令直接UID0、drop ALL/no_new_privs，权威与秘密外置 | 平台准入/账本、独立capture、Runtime证明整个Task停止 | Kali输出/exit只作执行器报告，不抗root篡改；需把collector bearer和Gate共享bearer移出，改Task/attempt/动作限定签名permit；改变逐Work“真实退出”强保证 |
| B：可信supervisor root，仅SETUID/SETGID/KILL；命令10002 | 可以保留较强本地幂等与逐命令执行记录 | 需要明确降权、卷权限、FD/环境和凭据隔离；同Task命令用户仍相同，不是多租户系统 |

严格明文模式下，A不能给KaliSETUID/SETGID/NET_ADMIN/NET_RAW/SYS_ADMIN，否则可绕过UID采集路径；因此A也不等于完整特权Kali。TLS服务私钥若仍留Kali必须只属于自己的Task/attempt端点，不得兼任平台客户端写身份或签发身份。

A会省去容器内两用户控制，但不是简单切runAsUser：当前permit_digest只是hash，真实权限靠collector回调；Gate发给Kali的共享bearer也会暴露。必须用既有签名设施签发用途受限许可，平台不信root执行器自报的强停止证明。若仍坚持每个Work.done必须证明全部后代实际停止，A会阻塞后继Work或要求另一个可信执行边界。

D-ROOT已由用户明确选择A：Kali内直接root、平台密钥与权威日志外置、重点保证Task级停止。Spec/Plan/验收/指令已据此替换双UID方案；Kali报告的弱保证和Task外部终止的强保证分开，其他黑板/复制版本合同不受影响。

## 7. 审查完成状态

源码事实研究、跨模块讨论、Spec定向复审及复制版本追加评审已完成。执行身份及D-NET已按用户选择收口。版本兼容、代理hook、root边界/网络/采集与实际CTF能力留待M0—M5实测，不能通过文档评审宣称实现完成。

## 8. 全局框架补充审查与用户纠正

用户指出此前子系统设计未覆盖整体执行链；追加Astra/high对Cairn角色/输出、Wuji Scheduler/容量、MAF接口以及Task配置→模型上下文做交叉核对。整体合同见Spec§2.1/2.2/8；用户随后授权Sol/xhigh开发。

| 当前源码发现 | 实施裁定 |
| --- | --- |
| reason/explore/report三个kind但first-use global/model池=1 | 区分角色与并发；新Task Explore上限可配置，不照搬固定2 |
| 真实任务无seed已Reason-first | 不另造Bootstrap Agent，纠正旧草案描述 |
| 任务配置已通过Profile.instructions实际进入MAF | 保留同一definition，补required等遗漏，不另建上下文真相库 |
| WorkResult仅存储/UI读取，problem Brief未消费 | 有版本有效投影→冻结snapshot→Brief；UI reader兼容 |
| Brief live attempts在两次resolve间可能变化 | 冻结后纯投影，不增加live结果查询 |
| problem context仍预读用不到的Artifact正文 | 提前选择上下文分支，旧路径保留 |
| 无Claim终态及input.resolved缺少Reason触发 | 平台一次真实work.settled与有效输入事件；排除Reason自触发 |
| claim_shared只唤醒未计进展；第二无进展窗口永久去重 | 增量/final共用去重，按窗口处理 |
| MAF支持response_format但Gate合同尚不接受 | 首批沿用同源schema提示+严格Host验证，不为未经验证模型强开新模式 |
| 仅有board_publish与自发refresh不足以说明及时获知 | 发布即共享；其他Agent下一模型安全边界获有界通知，正文真实读取 |

“最多2Explore”是主代理为验证提出的过小配置，用户明确否决其作为产品上限；已撤销并同步开发者。一个活动Reason借鉴Cairn的单规划租约，允许与Explore并行及多轮运行，其吞吐需实际验证，不宣称已证明最优。
