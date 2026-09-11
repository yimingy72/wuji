# Wuji 创建工作台交互原型

基于现有React/Ant Design和五套主题的独立原型，不连接API、模型网关或测试目标。只持久保存主题，页面刷新重置全部演示数据。

```sh
pnpm --filter @wuji/creation-workbench build
pnpm --filter @wuji/creation-workbench preview
```

入口：http://127.0.0.1:4186/tasks。端口冲突直接失败，不替换现有服务。停止时终止上述preview进程。

默认身份“管理员兼操作员”；左下角演示设置可切换角色/项目行为、响应丢失、原请求丢弃、模型检查unknown和网关阻断待确认。输入只留在本次页面内存；服务Key成功后清空，不写模型记录或浏览器存储。

完整交互与证据见[Spec](../../docs/stages/phase-1c-creation-prototype/spec.md)、[验收](../../docs/stages/phase-1c-creation-prototype/acceptance.md)；正式接口衔接见[D3-B清单](../../docs/stages/phase-1c-creation-prototype/backend-handoff.md)。本原型完成不表示D3-B业务已实现。
