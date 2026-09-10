# 项目背景与约束收口 Plan

- 状态：completed（文档交付；主目录两项同步尚未提交）
- 对应 Spec：[spec.md](spec.md)
- 基准：设计分支 0051651047daeeee3b8741c460f182d42e755238；主业务分支 381ae3a2205965ad6aab1ce787d490d2c02839f3。
- 批准依据：同 Spec；本次只执行文档治理。

## 任务与归属

主代理在 `work/worktrees/product-interaction/` 负责 AGENTS、README、project-context、Phase 1C 前置修订标记及本阶段记录，集成与验收。

开发代理 `gpt-5.6-sol / xhigh` 在独立 `work/worktrees/context-docs-cleanup/`、分支 `codex/context-docs-cleanup`，只负责 DESIGN、frontend-architecture、architecture-review、architecture-acceptance、development-workflow 和阶段 Plan 模板；提交后由主代理审查并集成。无契约、迁移或锁文件变更。

## 交付与验证

仅检查差异、新增链接和规则一致性，不安装、构建、启动服务或执行测试，不派独立业务测试代理。共享检查预算600秒，通过即停止。

提交设计分支；主目录同步 AGENTS 与指向最新索引的入口，不移动绑定运行 SHA 的 HEAD，这两项如保持未提交应明确交付。master 不变，业务测试证据不重标。后续在正常交付窗口集成文档并处理主目录入口差异，不修改运行 manifest 绕过 SHA 校验。
