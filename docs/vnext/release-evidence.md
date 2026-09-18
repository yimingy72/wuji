# P20 发布清单与最小验证记录

状态：`implementation-ready / cutover-not-authorized`。发布清单由
`scripts/vnext/assert_release_inventory.py` 根据实际 lock、package manifest、镜像/部署入口和源码摘要生成；不以空集合或历史文档文字代替扫描。

## 最小入口

```sh
./scripts/vnext/uv.sh run --frozen pytest \
  tests/vnext/test_archive_roundtrip.py \
  tests/vnext/test_release_inventory.py -q
./scripts/vnext/check_all.sh
```

`check_all.sh` 只覆盖本轮归档、发布清单和 v2 合同检查。它不停止服务、不切换流量、不删除旧数据；未运行的全量 K8s、浏览器、真实模型效果和生产切换保持 `not_run`。

## 发布不变量

- Python/npm 依赖、入口、Cairn 服务依赖和源文件摘要来自实际文件解析。
- 新发布物不枚举 legacy execution fallback；发现 Cairn、Pi 或 Claude 运行依赖时检查失败。
- 归档查询必须是只读路径，历史副本与新库分开核验。
- 代码来源和文档说明不构成停机、付费、生产部署或删除授权。

本地 HTTP 权限边界和终端截图已归档：[P20 证据包](evidence/P20/release-gate-20260918/README.md)。该包只证明未认证归档请求被拒绝；正向归档读取由隔离 SQLite 定向测试覆盖，不包含任何会话凭据。真实停机、生产切换和删除仍未执行。
