# 控制面 D1 Plan

- 状态：in-progress；日期2026-09-11；对应[Spec](spec.md)；用户本轮继续已授权范围内实现。
- 工作树：/Users/yym/Documents/ChatGPT/Wuji 自动化渗透平台/work/worktrees/phase-1c-prep；基准1da3ec6。

## 冻结方案

主代理负责本次设计、drafts.py Pydantic场景DTO、draft_routes.py路由、main.py接线、CursorCodec的task_drafts用途、0.5.0候选契约及生成器、版本/锁文件、临时PostgreSQL与ASGI定向验证、集成验收。页面和Task控制命令保持原有行为。内容是待确认意图，保存不解析模型ID或调用框架。

按需gpt-6-astra/low子代理只实现draft_store.py与0004迁移；不得设计接口、更换框架、修改其他文件、运行环境或继续拆代理。共享工作树唯一文件归属，主代理完成后审查。

DraftStore(authority)复用现有DatabaseAuthority实例：
- save(user_id,permissions_version,project_id,draft_id,expected_version,content,content_digest)->dict；content已由主代理DTO规范化，仍验证摘要匹配。
- get(user_id,project_id,draft_id)->dict；不可见raise ResourceNotFound。
- list(user_id,project_id,limit,position:TaskCursorPosition|None)->list[dict]；返回limit+1按created_at/id倒序，position.task_id表达草稿ID。
现有异常沿用ResourceNotFound/CommandForbidden/FreshAuthorityInvalid/VersionConflict/CommandValidationFailed/AuthorityUnavailable。

保存先用户锁、项目重新鉴权、核对permissions_version；INSERT ... ON CONFLICT DO NOTHING RETURNING先处理首次创建。冲突后只读取当前归属可见行FOR UPDATE。expected_version=当前version执行UPDATE version+1；expected_version+1=当前version且摘要一致为紧邻重放；其他409。初始version1，expected_version>0且不存在返回404。缺失归属的全局ID冲突返回404。SQLAlchemy错误脱敏转AuthorityUnavailable。

迁移表task_drafts(id,tenant_id,project_id,user_id,content jsonb,content_digest char64,version bigint,created_at,updated_at)。内容digest以b'wuji-draft-v1\\n'+规范化sort_keys/separators/ensure_ascii=False JSON计算（标记包含实际换行，不是反斜杠n）。写/读RLS遵守Spec；更新列白名单不包括归属。不设默认/虚构模型方案、不写Cairn表。迁移编号由此子任务独占，根EXPECTED_REVISION由主代理更新。

## 执行顺序和验证

1. Spec/Plan落盘与分支固定；并行实现DTO/路由/契约和存储迁移。
2. 接线与审查；固定候选SHA。
3. 使用已有.venv及本机PostgreSQL执行一次定向pytest；全程持有自有临时数据库生命周期，finally核对自有目录停止。身份使用临时种子+真实session表，不用模型或oidc网络。
4. 生成契约并检查新增响应、构建API包；测试失败按trace只复测相关项，通过即停。
5. 验收记录绑定实际SHA/run_id/命令/退出码/限制；主业务HEAD/master不前移，根索引指向本分支。当前工作树无CodeGraph，不自动新建索引。

依赖复用：Pydantic、SQLAlchemy/psycopg、Alembic、CursorCodec、现成用户锁和RLS、OpenAPI生成器；无新增模型客户端、Harness、预算引擎。Pi/Cairn/LiteLLM候选和原4次真实模型额度不变。D2—D4先完成各自具体Spec/Plan，不为显示开发进度加入尚无消费者的接口。

验证辅助：gpt-6-astra/low子代理只编写tests/control-plane临时PostgreSQL与定向用例；主代理统一执行，不另开生产或并行数据库。新响应schema名SavedTaskDraft/SavedTaskDraftPage，保留旧TaskDraft。
