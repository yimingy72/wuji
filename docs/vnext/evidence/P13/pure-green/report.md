# P13 纯投影片验证记录

日期：2026-09-13。代码与测试提交：`78a26e35445ecf75fc479bbe8977f584cdc8e703`。

执行命令：

```text
./scripts/vnext/uv.sh run --frozen pytest tests/vnext/test_projection_builder.py -q
```

实际结果：退出码 0，`9 passed in 0.03s`。本次文档收口直接复用已保存的[文件绑定](binding.json)与[原始结果](result.txt)，没有重跑测试。

验证范围仅为纯函数投影：精确 revision 节点身份、可信 assessment 的 Claim/Fact 展示、关系精确端点和稳定身份、缺失端点过滤、重复冲突拒绝、payload/ref 核对、公开字段白名单，以及 AgentRun 固定 `ref@1`。未运行数据库、HTTP、网络或截图验证，不表示 P13 持久快照、历史、分页、权限或 API 已完成或 accepted。

执行归属：RED、GREEN 和定向边界检查由主代理委派的 SOL/xhigh 执行，不是主代理亲自运行的独立测试，也不属于第三方认证。P05 controller-review 中已有“主控制器独立复核”措辞保持历史原样，本报告不沿用该措辞描述本次 P13 执行者。

完整 P13 仍等待 P06 迁移所有权交接。后续需用真实 criterion dependency 定向复现并修复 `SnapshotRepository.create` 对旧 `goal_criterion` KnowledgeRef 的消费，改用既有 `GoalCriterionRef`，不得扩展知识实体枚举。
