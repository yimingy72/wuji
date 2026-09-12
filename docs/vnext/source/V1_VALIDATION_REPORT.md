# 文档级验证报告

日期：2026-09-12。验证对象为本次生成的文档包。

| 检查 | 结果 |
|---|---|
| 原始上传文件逐字节保留 | PASS；SHA-256 `8442b71239a23d2ebe0255827df56a9cd73a0b60a3fa76b46b8c4075d598ba97` |
| Spec 需求编号 | PASS；32 项，完整覆盖 |
| 命名验收用例 | PASS；40 项，均有需求与Plan映射 |
| Plan 任务 | PASS；19 项，P00–P18 |
| 任务依赖 | PASS；无环，引用任务均存在 |
| 文档相对链接 | PASS；19 个；原始草案历史链接不改写、不计入此项 |
| Markdown 代码围栏 | PASS；Spec/Plan 成对 |
| Python 测试片段语法 | PASS；16 个经 ast.parse；未执行 |
| JSON 示例/映射 | PASS；可解析 |
| 未完成占位符扫描 | PASS；无 TBD/TODO/FIXME |

## 本次没有运行

产品单元测试、PostgreSQL并发测试、真实MAF调用与压缩、React Flow浏览器构建/渲染、TypeScript类型检查、Mermaid渲染、Runtime停止、网关计费及真实效果/性能测试均 **NOT RUN**。这些步骤写在Plan中，不能因为文档级检查通过而认定它们已通过。

本文中的Python片段是目标契约测试，依赖Plan要求新建的代码与夹具，不是可在当前旧仓库直接通过的实现。

## 人工一致性复核

文档自检发现并修复了 REQ-017 漏映射及一条双测试命令的空格问题。另补全最小线协议与数据库约束。修订了 imported_unverified 不直接进入 FactLedger、可信采集必须位于不可改写信任域、完成时结算剩余工作、采集权限错误码、只读归档API和测试夹具operation映射。仍需实施者按G1验证真实SDK边界，而非用文档推断。
