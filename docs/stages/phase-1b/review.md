# Phase 1B 首批方案评审

- 日期：2026-09-09。
- 基础代码：`70668be2d5d42c9468764399b5be2d5157951943`。
- 主代理负责决策；独立评审为 `gpt-5.6-sol / xhigh`，只读核对当前契约、权限与路由，不执行测试。
- 结论：B1方案review-ready，实施not-started；没有创建目标任务、修改数据库或启动测试。本次在Default模式完成材料准备，未声称切换Plan模式或获得新阶段实施批准。

## 已修正的实现缺口

| 发现 | 决定 |
| --- | --- |
| B1尚无创建接口，不能提前暴露task.create或返回虚假的可创建状态 | OpenAPI升0.3.0，新增task.preview与CREATION_UNAVAILABLE；B1范围结果仍可查看，B2才开放真实创建 |
| 当前ProjectRecord无角色，Project响应硬编码project.read | 同一受限事务读取有效tenant/project membership角色，两级取最小权限，再与本批实现能力求交；列表/详情/写策略一致 |
| 任务新路由不在当前登录回跳白名单内 | API security.py、web routing.ts及OpenAPI登录/回调声明同步增加B1精确tasks/new路由 |
| 预览缺500声明，且继承无来源409/410 | 显式声明Session+CSRF，补500；删除预览无来源状态，scopes保留分页410；明确404/403/422与200 blockers边界 |
| 没执行器被混为没Adapter，阻断任务管理独立交付 | B2允许接受queued任务；运行资源可用性由执行许可流程核验，MISSING_ADAPTER不代指worker未部署 |
| queued任务取消引入无必要中间态；未发许可却声称revoked | B2同事务直接cancelled并写回执/事件；新增not_granted，terminal允许not_granted或revoked；不增加后台恢复程序 |

## 首批交付与验证范围

B1新增授权记录、不可变Scope版本、短时预览三类数据及两个API；复用现有事务、管理入口和前端基础。规范化算法、RLS、权限、分页、表单修订号与失败显示详见[B1 Spec](b1-spec.md)。已有运行文件schema和集群清单保持现有版本，迁移由唯一负责人同步健康检查期望revision。

只计划纯计算输入向量、四类API场景、一次页面预览和必要构建，所有代理共享10分钟；其余场景集中后测。Phase 1A的73个API、6个生命周期与三个延期回调不因B1开发重新全跑。本轮仅检查文档差异，不将方案评审当作产品验收。

评审文件在独立 `codex/phase-1b-review` 分支维护，当前主工作树及运行中的Phase 1A保持 `70668be`，避免仅提交文档就使运行记录SHA失配。B1批准实施时从明确基线集成评审产物后再分派开发。
