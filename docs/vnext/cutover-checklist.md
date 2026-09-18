# P19 离线归档与切换准备清单

状态：`dry-run only`。本清单不授权停机、入口切换、旧数据删除或旧服务重启。

## 开发副本

- [x] 以只读模式读取 SQLite/JSON 副本并生成 `wuji.legacy-archive.v1` manifest。
- [x] manifest 保留原始 ID、revision、source hash、关系、产物元数据和权限映射。
- [x] `ArchiveImporter.import_archive()` 只写 `vnext.archive_*`；`vnext.work_item` 保持为空，`executable=false`。
- [x] 归档查询从 SQLite 直接读取，不需要 Cairn/Pi 或任何旧服务。
- [x] Claim 以 `LegacyClaim` 展示，不能直接变成新的受支持 Fact。

## 真实切换前必须由独立运维授权

- [ ] 禁止旧系统新增执行，并逐个核对旧 Run、工具和未知状态。
- [ ] 完成副本导出、计数、摘要、权限与产物校验。
- [ ] 在独立新库/命名空间完成发布清单与健康检查。
- [ ] 获得明确的停机/入口切换批准后，才允许切换新 Task 入口。
- [ ] 失败时进入新系统只读维护，不自动回退到 Cairn；删除旧卷另行批准。

本轮未执行真实停机、生产入口切换、旧卷清理、外部目标请求或付费模型调用。
