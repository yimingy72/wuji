# D3-A 实施Plan

状态in-progress；基准5940d15；用户已批准修订版。当前会话直接实施，不另建任务或调用开发代理。

## 方案和分工

主代理维护spikes/creation-workbench全部代码和文档。复用@wuji/theme、Ant Design6.6.3、React19/React Router、D1/D2生成类型，依赖版本沿用现有锁定版本；不改共享主题或正式apps/web/API。State模块分客户端pending与服务端Map，通过独立上下文generation防迟到响应跨项目。领域模块实现纯本地host/协议端口与排除优先，不解析DNS。

场景表单/Scope editor/摘要/详情复用相同范围展示组件；创建时deep clone快照，模型后续变化不改Task历史。模型页维护服务/方案不可变版本，Key不存模型记录，仅待提交表单和unknown冻结请求临时持有，成功或离开/换身份清理。未知检查重放只查记录；重新检查为显式新操作。

样例仅包含一个明确标为演示价目的模型方案，无虚构运行中任务。异常控制集中在演示设置：下一次创建成功/已创建但丢响应/明确拒绝；下一次查询404；模拟刷新；模型服务保存丢响应、检查unknown、网关block待确认；角色和项目切换。演示数据可重置。

路由/tasks、/tasks/new、/drafts/:id、/tasks/:id、/settings/models。默认主题silver，通过共享tokens应用到root和浮层。创建页4步+右摘要，窄窗口摘要折叠。页面仅显示业务状态与小型演示标记，具体模拟说明收进设置。

## 交付顺序

先Spec/Plan→组件API查询→领域/内存状态→工作台/表单/模型页→pnpm锁文件增量安装→固定候选构建/antd lint→4186静态预览和Codex浏览器四条流程→修复受影响项→截图/验收/本地提交。保留主目录381ae3a和master28fcd44，不改旧服务、私有运行记录或原型。当前工作树无CodeGraph，按约定rg和读取。
