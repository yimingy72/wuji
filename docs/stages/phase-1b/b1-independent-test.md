# B1 独立测试记录

- 状态：`draft`，仅完成最小用例编写；尚未绑定最终集成候选 SHA。
- 用例初稿作者：`gpt-5.6-luna / xhigh`；后续接口对齐与执行者为主代理。原代理恢复和同模型新建均被工具以agent thread limit reached拒绝，已向用户报告。
- 工作树：`/Users/yym/Documents/ChatGPT/Wuji 自动化渗透平台/work/worktrees/phase-1b-test`。
- 编写基线：`b59508891774e1c08558179015a8a74cadb8aed1`。
- 本次没有安装依赖、启动服务、构建或执行测试 collection。

## 已准备的最小覆盖

- `tests/unit/test_scope_policy.py`：默认 HTTP(S) 端口与域名大小写归一，`/public/a` 通过，`/publicity` 与排除前缀拒绝，编码点段 `%2e%2e` 与编码斜杠 `%2f` 拒绝。纯函数导出名以小适配层集中等待 B1-A1 最终公布；首轮执行前需按实际公共导出收窄适配。
- `tests/api/test_phase1b_scopes.py`：动态从 `GET /projects/{project_id}/scopes` 读取 Scope；覆盖合法预览（规范化结果和 `CREATION_UNAVAILABLE`）、越界路径、跨项目 Scope、Viewer 拒绝和缺少 CSRF 拒绝。没有读取 run-file 中未定义的 Scope 字段，也没有访问私有凭据。
- `tests/platform-browser/05-scope-preview.spec.ts`：复用既有正常 Keycloak 登录 helper，走 `/projects/{project_id}/tasks/new`，选择 Scope、填写受控输入、提交预览，断言结果显示且未开放创建；执行时保存一张不含密码的预览截图到 run 的 ignored 证据目录。
- `tests/api/test_projects_permissions.py`：按双层角色精确断言 `project.read` 与 `task.preview` 权限投影。

## 待最终候选 SHA 后对齐

1. 主代理已按B1-A1导出固定normalize_url/normalize_task_draft/evaluate_scope与ScopePolicyError，删除猜测兼容层；不改变向量或扩展测试范围。
2. 依据最终 Scope seed 的列表结果确认浏览器控件可访问名称；仍只保留一条真实登录预览主流程。
3. 既有resilience断言已更新为A当前迁移revision 20260910_0002；未因此运行旧套件。
4. 仅在主代理提供固定候选 SHA、run-file 与正式 serve-only 环境后，按 B1 预算执行四类 API 和一条浏览器用例；绑定实际被测 SHA，记录通过、失败和待测项。

## 约束

本记录不声称任何测试已通过。未覆盖真实 Keycloak 回调捕获专项、创建/执行、扩展 URL/IPv6 矩阵、Scope 翻页和全量平台套件。执行阶段遵守共享 600 秒预算、最多两轮同类脚本排查，并在完成必要检查后停止。
