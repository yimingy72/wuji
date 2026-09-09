# Phase 1A 方案评审记录

- 日期：2026-09-09
- 评审基准：`28fcd44eebc205a35735d3e7b60a308ce5f749bc`
- 本轮范围：用户明确选择“先完成方案评审”；只修订规划，不批准或启动业务实现
- 参与者：主代理；独立后端设计复核 `gpt-5.6-sol / xhigh`；独立验收设计复核 `gpt-5.6-sol / high`
- 产物：[Spec](spec.md)、[Plan](plan.md)；[运行验收](acceptance.md) 仍为 `not-tested / pending`

主架构方向保留：React/Ant Design、Python/FastAPI、PostgreSQL、Keycloak OIDC，复用现有 Docker Desktop Kubernetes。评审补齐进入实施前必须明确的行为、契约和任务依赖。下表“已修订”表示写入设计，不代表运行验证通过。

## 发现与处理

| ID | 原草案缺口及触发场景 | 本次修订 | 状态 |
| --- | --- | --- | --- |
| R1A-01 | Plan §1 同时固定 uv 0.10.8 和 Python 3.13.15，但本机 uv 下载清单没有该 Python 版本；新机器不能按原方案自动安装 | 固定项目专用 uv 0.12.11，使用其已包含的标准 GIL Python 3.13.15 元数据；安装/校验由 CORE 执行，保留系统 uv/Python | 已修订 |
| R1A-02 | Spec §3 只有“state 一次性”，没有服务器状态适配和并发领取；回调失败的原始 JSON 会占据浏览器登录页面 | Authlib 负责协议，Wuji 原子领取服务器握手；明确替换/交换中/并发边界、query 回调及固定站内303错误页，不回显协议参数 | 已修订 |
| R1A-03 | Spec §3/§5 未规定 Session 必需字段、空闲续期、CSRF重启保持、permissions_version递增及退出失败 | 固定会话字段/数据库时间条件续期、独立CSRF；权限变更/版本/审计同事务；禁用撤销会话；前端区分遮蔽与已确认注销 | 已修订 |
| R1A-04 | 当前 Permission 只有 task/artifact，公开端点会继承根安全要求，health可能误加/api/v1；项目分页名称/错误及校验生成未固定 | 追加project.read、明确实际能力交集和security覆盖；health操作级根server；保留limit/cursor并固定失效规则；Ajv构建时生成校验器，与真实API验证分开 | 已修订 |
| R1A-05 | Spec §5 的角色与RLS文字尚不能直接写迁移；可能使用SET ROLE、owner代验或单列外键；仅按租户成员过滤还可能放行同租户其他用户的项目 | 三凭据/连接入口、四表RLS、事务上下文和复合外键；成员行强制当前user_id，Project精确匹配该用户项目成员关系；补同租户互斥项目反例 | 已修订 |
| R1A-06 | Plan §4/§5 的共享manifest、测试配置/fixture归属及完整生命周期不明确；正式E2E可能误入原型4175或依赖本机集群的Ubuntu CI | 固定CORE/SERVER/WEB/TEST文件归属；CORE先交付；测试独立目录/配置；run隔离、转发监督、finally清理；CI只承诺无集群检查 | 已修订 |
| R1A-07 | P1A-02/06/07 只列反例名称，没有产生错误ID Token、独立DB失联、未迁移状态及迟到响应的可执行方法 | 真实Keycloak+受控协议issuer；仅中断API专属DB转发；空DB+独立API；撤权提交/新404/释放旧200的黑盒时序；故障恢复继续读取原数据 | 已修订 |
| R1A-08 | 主题共享/偏好有方向，但未明确Provider稳定性、浮层上下文和实际可测状态；P1A没有业务表单却要求表单测试 | 单份公共theme包、稳定ConfigProvider/App上下文、设备偏好与URL临时覆盖分离；测当前项目/游标分页保持，后续有表单时再验草稿 | 已修订 |

## 证据与判断边界

本轮 CodeGraph 定位了原型主题/上下文；契约 YAML 与部分配置无适用结果时回退直接读取。核对当前 `Session.permissions_version`、`Permission` 枚举、`PageSize.name=limit`、根 SessionCookie 安全要求和 `/api/v1` server。Ant Design CLI 的 `ConfigProvider` 元数据支持统一 theme；正式浮层使用上下文的决定依据官方主题说明。相关资料已在 Plan 对应段落引用。

本机只读工具链结果：`uv --version` 为 0.10.8；`uv python list 3.13.15` 没有结果；`uv python list --all-versions 3.13` 的可下载版本最高为3.13.12，本机另有Miniforge的3.13.14。官方uv0.12.11清单已核对标准GIL的darwin-x86_64及linux-x86_64 Python3.13.15条目；未下载或执行该版本解释器。

验收设计复核确认本机docker-desktop v1.36.1 Ready、amd64、默认hostpath；wuji-dev/wuji-test尚未创建。数据库故障方案经过第二次独立设计复核：停止API专属port-forward可以验证API→DB路径失联，同时Keycloak的集群内数据库路径保持可用；不能把此结果宣称为PostgreSQL Pod故障隔离验证。

## 交付与后续

本次仅形成待实施的设计，Spec/Plan继续为draft。CORE、SERVER、WEB和产品测试任务尚未派发；上述两个子代理执行的是只读审查。实际安装兼容性、镜像digest、迁移/RLS执法、OIDC成功/失败、前端页面和P1A-01–10仍须实施后绑定提交SHA取证。既有21项契约/12项原型浏览器测试不能转记为本阶段结果。

批准实施后，按CORE公共工程与契约 → SERVER/WEB并行 → 独立测试 → 修复/主代理验收推进。主代理负责已经选定的方案，子代理遇到实质冲突须交回修订，不自行换架构。本评审文件的提交由Git历史查询，不回填自身SHA。
