# P13 → P14 后端消费交接

P13 后端运行验证绑定 `44ddc68e48e1c36974cec7e705d1cd3812c7a031`。正式容器使用：

```python
projection = ProjectionRepository(uow)
app = create_app(
    token_verifier=token_verifier,
    routers=[create_topology_router(projection)],
)
```

`create_topology_router` 独占冻结的三个 GET：`/api/v2/tasks/{task_id}/topology`、`/snapshots`、`/records/{record_type}/{record_id}`。不要同时挂载旧 `create_records_router`，不要增加 fixture fallback。

前端续页必须原样保留 mode、snapshot、node/edge limit，并只替换 cursor；query、主体、ACL 或 projection binding 改变时旧 cursor 返回 404，应重新获取视图。节点按精确 `entity_type:id@revision` 合并，history mode 的 `allowed_actions` 为空。未知/过期历史按 410 处理。

当前后端未提供 Layout 或 ViewStream 路由。P14 接线不能把固定 DTO demo、旧 records router 或本地 mock 当成真实 API 成功；对应浏览器验收另行执行。
