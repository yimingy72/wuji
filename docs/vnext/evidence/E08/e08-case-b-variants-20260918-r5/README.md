# E08 CASE-B 一致变体 r5：信息驱动链路完成，正式判据保持未评估

- 日期：2026-09-18
- 代码：`81174f99264bcd5b69747a04493832a75a2d800e`
- Task：`5b612f6b-39b3-4a69-a0ab-c3a81723cafc`
- 模式：`mechanism_synthetic`
- 最终试次状态：`partial / not_assessed`

## 已验证的动态链路

1. 正式 `POST /api/v2/tasks` 返回 `201 Created`。
2. owner 四阶段成功：prepare、activate、wire、capability。
3. 第一条 Explore 读取 `materials/record-a.json`，产生 Claim，正文包含 `version: 4.2.0`。
4. 后续 Reason 根据第一条真实 Claim 提出此前不存在的 Intent，问题指向 `materials/record-b.json`。
5. 第二条 Explore 正式调度执行并读取 `record-b.json`，得到 `version: 4.2.0`。
6. 后续 Reason 产生候选比较 Claim：两条记录一致，版本为 `4.2.0`，并引用两份材料。
7. 完成提案被真实消费者评审；`completion.reviewed` 返回 `decision=wait`，因为正式 `record-comparison` Judgment 尚不存在。

这证明了“观察 → 非预写 Intent → 新工作 → 新证据 → 改变判断”的平台链路；候选 Claim 没有被冒充为 Fact/Goal 已满足。

## HTTP 与截图证据

- [完整创建请求/响应](raw/create.http)
- [完整取消请求/响应](raw/cancel.http)
- [数据库最终回读](raw/db-final.txt)
- [运行状态截图](screenshots/consistent-final-terminal.png)

Bearer 已脱敏；原始 response headers/body 也分别保留在 `raw/`。

## 结束与限制

正式 cancel 返回 `202 Accepted`，Task 收敛到 `cancel/quiescing`；取消是因为完成评审明确缺少正式 Judgment，不是因为模型自报失败。该 r5 记录只覆盖一致变体；后续冲突与信息不足变体分别见 [r6](../e08-case-b-variants-20260918-r6/README.md) 和 [r7](../e08-case-b-variants-20260918-r7/README.md)。真实模型仍为 `blocked_configuration`。
