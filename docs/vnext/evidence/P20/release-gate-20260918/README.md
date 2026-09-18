# P20 本地发布门与归档 HTTP 边界

- 被测代码：`a4d7dc9` 加上本次证据记录提交
- 范围：只读归档路由的未认证拒绝、归档/发布清单/合同定向测试
- 不包含：真实停机、生产入口切换、旧卷删除、外部目标或付费模型调用

## 证据

- 截图：[本地终端验证](screenshots/archive-unauthenticated-terminal.png)
- 完整 HTTP 报文：[archive-unauthenticated.http](raw/archive-unauthenticated.http)

HTTP 报文中的 `401` 是预期的权限边界：没有 bearer 身份时不得读取归档。归档正向只读读取由 `test_archive_roundtrip.py` 在隔离 SQLite 中覆盖；本包不写入任何会话凭据。

## 命令与结果

```text
./scripts/vnext/uv.sh run --frozen pytest tests/vnext/test_archive_roundtrip.py tests/vnext/test_release_inventory.py -q
6 passed in 0.59s

bash scripts/vnext/check_all.sh
P19/P20 minimal checks passed (archive, release inventory, v2 contracts).
```
