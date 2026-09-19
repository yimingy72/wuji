# 现场未验收：Wuji 首用操作说明（A8 初始版）

当前不能向用户宣称现场已可用。A8 已修复无害 F1/F2 fixture 配套的 HTTP 控制 driver，完成实际 BFF 协议定向验证和 A1/A5 独立局部复核；87 项静态矩阵保留 not_run。没有固定集成 SHA 的完整浏览器/服务链实测，也没有访问指定现场实例。

## A0 集成后的真实操作路径

1. 在受权项目的正式工作台创建一个新 Task，确认 Scope、入口 path/query、Goal、已发布 Profile 和预算；创建后停在 `ready/pause`，刷新/readiness 不应访问模型或目标。
2. 通过工作台显式 `start`。driver 将核对 `TaskCommand` 的 `expected_version`、稳定命令回执、`launch` 阶段和实际 attempt/Pod/receiver 身份。
3. 读取由真实工具保存的 Artifact/Observation。材料必须通过已保存的 source digest 和 `wuji.model-material.v2` representation digest 进入模型请求；不能只给 Artifact 引用。
4. 检查后续 Reason 的 `read_set` 和 Intent/Claim 引用确实指向该次材料。Reason 不获得目标工具；需要补证时由受控 Explore/Intent 继续。
5. 通过用户入口 pause/cancel，分别查看命令受理、Task 状态、Run 进程退出、ToolOperation 结算和环境清理；`202` 本身不等于已停止。

## 当前不可使用边界

- 本文没有可点击的真实工作台地址、Task、Run 或现场回执；不要使用固定历史 Task 代替新建。
- 用户已批准 DeepSeek deepseek-flash、金额无上限及官方价；2026-09-19将自建HTTP实例替换为 `http://39.102.208.182`（旧地址不再使用），A0负责配置与现场实测。DG2仍需实际SecretRef、usage和费用链记录；A8不读取provider Key。
- F1/F2 是 `mechanism_synthetic` 机制夹具，不能证明真实模型自主效果，也不能证明现场目标可达。
- 登录/浏览器操作、超出已发布只读工具的能力、目标网络扩散和破坏性动作不属于本轮首用范围。

现场结论标题必须继续写“现场未验收”，直到 DG1、DG2 适用项和 DG3 的真实同构建证据全部满足。
