# D3-A 原型评审记录

- 状态：implementation complete / review-ready；用户交互评审待完成，不标为正式业务验收。
- 日期：2026-09-11；基准5940d15；分支codex/phase-1c-creation-prototype。
- 当前实现/构建候选：`b6afc12b2c7ef0ec613ff395f92eb5e2274be9a4`；主要浏览器流程被测`0bf9fa7580d585c6639f77c70a7b11e7f023030c`。
- 补充迟到响应检查被测`efb270c`；最终日期本地化/真实刷新提示在b6afc12构建上浏览器复核。
- 当前会话主代理完成设计、实现、浏览器走查和验收；本批未使用子代理，非独立测试。
- [Spec](spec.md)、[Plan](plan.md)、[D3-B衔接清单](backend-handoff.md)。记录自身提交从git log查询。

## 已交付

独立spikes/creation-workbench，任务/草稿、Web四步向导、包含/排除/期限、模型/金额、创建四态与原键恢复、待启动详情和取消、D2服务/方案版本表单、明确计价和平台/网关撤销状态。保留其他四类草稿入口、五主题和演示设置。

默认匿名；不提供路径ACL、账号、Cookie、任意代理或MCP地址。数据仅在浏览器内存，只有主题保存到localStorage；原生页面reload清空演示数据，“模拟刷新”只丢弃原请求并保留模拟回执及标识。CSP限制为本地资源，不连接实际API/模型/目标。

## 实际走查

| 项目 | 结果 | 浏览器证据 |
| --- | --- | --- |
| R1 Web主流程 | passed | 输入app.example.com入口，包含example.com及子域；排除example.com时入口被排除/范围为空，创建禁用但草稿保存可用。改排除admin.example.com、填写明确截止时间和金额后可确认；确认页及最终详情包含/排除/协议端口一致 |
| R2 创建结果不明 | passed | 模拟已经创建但丢响应，先呈现submitting再unknown；首次回执查无结果后仍待确认；任务页显示任务1且禁止新创建。模拟刷新后不再提供原请求重试；核对进入同一个已观察Task URL，没有第二个Task |
| R3 D2表单 | passed | 服务V1创建V2时Key为空，直接保存被拒绝；填写仅用于演示的非真实Key后保存成功，只显示已配置。缺价方案能保存和检查，但发布提示补价；新方案版不继承检查，价格来源/输入输出填写后缺缓存模式仍不能保存，显式选择后保存、检查并发布成功 |
| R4 撤销 | passed | 撤销原通用评估V1显示“平台已禁用，网关阻断待确认”；返回原草稿仍显示该版本及不可用提示，创建禁用；另有已发布方案也没有自动替换 |
| 布局/主题/键盘 | passed（代表性） | 雾银与亮石墨；900宽时右摘要改折叠，展开内容可读。稳定页面scrollWidth=clientWidth=885（viewport900），无页面水平溢出；Tab从排除主机到移除按钮。检查后清除viewport override，恢复雾银 |
| 收尾修正 | passed | 定向假计时检查旧身份回调不能改后来同项目新命令；浏览器日期月份9月、星期一至日显示中文；真实reload缺失内存草稿显示“演示内容不存在或已重置”并可返回任务页 |

浏览器使用Codex in-app browser/CUA，未读写页面隐藏应用状态或调用真实接口。个别操作定位遇到浮层关闭动画、图标组成的可访问名称和已消失toast；按新快照定位后完成，不以瞬态定位超时冒充业务失败，也未反复重跑整套流程。

## 构建与检查

- 冻结依赖版本均沿用现有仓库；新增workspace importer及dayjs1.11.23直接声明，包来自本地缓存。未升级现有依赖。
- 初始def4add构建在TS控制流收窄处失败（异步状态被推断为never），Vite尚未执行；修正为重新读取当前状态后通过。
- `pnpm --filter @wuji/creation-workbench build`：0bf9fa7及后续实际修正对应构建exit0。当前b6afc12源码经tsc/Vite成功打包。
- `pnpm --filter @wuji/creation-workbench exec vitest run --config vitest.config.ts`：1个定向竞态用例通过，exit0；没有增加无关单元矩阵。
- `pnpm exec antd lint spikes/creation-workbench/src --format json`：exit0，无deprecated/a11y/usage错误；7条关闭Select虚拟滚动的性能提示保留（少量原型选项）。最后tasks提示修改仅检查该文件，2条同类提示。
- Vite有单包约806KiB的体积提示，本批不扩展打包优化；正式接入可按路由拆分。无错误级浏览器日志。

最终MissingDemo提示只修改缺失内存记录的页面分支；未改变已走查创建、范围或模型逻辑。迟到保护只收紧原回调写入的key判断；复用R1—R4旧SHA证据，另补定向竞态测试，不冒称全部在最终提交重跑。日期与刷新提示在最终构建实看。

## 截图与入口

入口：[创建工作台](http://127.0.0.1:4186/tasks)。原型静态preview已启动，Codex浏览器保留了当前示例草稿。启动命令为`pnpm --filter @wuji/creation-workbench preview`；端口4186严格检查，不接管旧端口。当前server启动于0bf9fa7，后续只替换静态dist并按要求reload验证，未改任何正式运行SHA记录。

忽略目录artifacts/phase-1c-creation-prototype包含：
- scope-delivery.png：最终候选范围编辑页；confirm-silver.png：确认页；task-ready.png：恢复后的同一任务详情。
- create-unknown.png：结果待确认；models-revoked.png：平台禁用/网关待确认。
- narrow-slate.png、scope-narrow-slate.png：窄窗口深色主题及摘要。
- build.json/log、final-checks.json、delivery-checks.json、antd*.log、race.log；preview.json记录当前监听进程及构建来源。

截图含合成域名、示例金额和人工填写的2030截止时间，它们不是产品默认值或真实授权。

## 限制与下一阶段

真实刷新会重置模型、草稿、任务及回执，不能把此原型用于保存真实工作。只有Web可模拟创建；其他四类仅草稿。Task均未执行，取消不表示验证过Runtime停止；无Cairn/Agent/Kali/网关/数据库调用。

没有验证完整主题/设备/无障碍矩阵、高级规则所有组合或正式后端流程；共享主题和旧平台证据按原SHA保留。待用户评审后才进入D3-B公开接口、Scope兼容、快照及ready生命周期实施。主目录381ae3a、master28fcd44和现有服务保持原状。
