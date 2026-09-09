# 开发基线 Plan

- 状态：in-progress；用户已批准协作流程，本文件记录执行拆分
- 日期：2026-09-09
- 对应：[Spec](spec.md)

## 固定方案

先显式审查项目文件，配置仓库本地 Git 身份并建立首次快照。主代理在 `codex/development-baseline` 集成；各子任务从明确快照创建独立分支/worktree。保留 `master`，通过阶段验收后快进到已集成结果。

新建阶段模板和指南均为 Markdown，不引入额外运行框架、发布自动化或镜像。现有测试命令保持不变，优先定位已安装的 Node 24.20.0 供命令使用，不更改系统默认 Node。

## 分工与依赖

| 任务 | 执行者 | 允许修改范围 | 依赖与交付 |
| --- | --- | --- | --- |
| BASE-01 | 主代理 | AGENTS.md、本阶段 Spec/Plan、Git 本地设置 | 首次文件/密钥检查、项目快照、阶段与 worktree 建立 |
| BASE-02 | SOL/xhigh 开发代理 | docs/development-workflow.md、docs/stages/_templates/；spikes/frontend/src/shared/model.ts 仅清理文件末尾多余空行 | 依赖 BASE-01；实现指南/模板并修正首次暂存检查发现的空白问题，本地提交并回报 SHA；不改契约/运行逻辑/锁文件 |
| BASE-03 | SOL/high 独立测试代理 | 本阶段独立测试报告；其余只读，测试产物进入 ignored 目录 | 依赖可测试 SHA；固定工具链运行现有检查、核查 B01–B08，提交报告 |
| BASE-04 | 主代理 | README.md、docs/predevelopment-plan.md、本阶段 acceptance.md | 集成 BASE-02，检查最终差异、复核证据、记录测试 SHA 与未覆盖项 |
| PLAN-1A | 主代理，SOL/xhigh 只读调研协助 | docs/stages/phase-1a/spec.md、plan.md | 调查实际开发环境和成熟依赖；主代理确定草案，未授权 Phase 1A 业务实现 |

公共契约、依赖锁文件、数据库迁移本阶段无计划变更；若基线失败暴露必须修复的问题，主代理先记录原因并指派唯一实现者，不由测试代理自行修改预期。

## 验证入口

```sh
pnpm install --frozen-lockfile
pnpm check
pnpm exec antd lint spikes/frontend/src --format json
pnpm build
WUJI_BROWSER_CHANNEL=chrome pnpm test:e2e
```

记录实际 Node、pnpm、Chrome 与被测试 SHA。Playwright 使用 4175，评审原型继续使用 4173；端口被占用时先识别拥有者，不杀其他工作流进程。依赖下载失败不能标记冻结安装通过。Ant Design 已知小列表虚拟滚动提示记录边界，不直接扩大阈值或删除检查。

文档通过相对链接、模板必需字段、引用一致性和 Git 暂存清单检查；不为 Markdown 文字镜像编写低价值单元测试。测试报告晚于被测提交落盘时，只复查报告/文档差异；若运行源码或配置变化，再运行受影响检查。

## 完成规则

开发与独立测试返回准确提交 SHA、变更清单和结果；主代理确认 B01–B08，并将不适用/未完成项明确列出。阶段集成与验收记录提交后更新 `master`，保留子任务分支供追溯。Phase 1A 文件仍为 draft，下一阶段需完成其具体 Plan 评审。
