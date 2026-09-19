# 首用验收记录

状态：in-progress；尚未放行。2026-09-18 开工基线 `b1ba8ec`，源包校验通过不是产品测试通过。

| 关口 | 当前状态 | 证据要求 |
| --- | --- | --- |
| DG0 代码与合同 | 初次 fail；修复复核中 | 生成合同、定向权限/状态检查、A8 独立复核 |
| DG1 机制首用 | not_run | 固定版本、真 PostgreSQL/服务/MAF、自建目标/合成上游、浏览器创建到停止 |
| DG2 DeepSeek | not_run | 有效预算/数据许可、真实供应商原生工具往返、正文/usage/费用证据 |
| DG3 用户现场 | not_run | 明确获准单实例/安全入口、同构建配置、真实工具与停止证据 |

完整结果与未运行原因将在执行后追加；历史阶段结果保留其原 SHA 与范围。实现者自测不充当 A8 独立验收。

2026-09-19：A8 在固定 `5cdbd170939f1d2e410868ab591381331f5cdba9` 独立执行一次完整 Python：745 collected，742 passed / 3 failed / 0 skipped，exit 1。三项为 ViewEventBatch v3 示例/机器索引/公开路由清单漂移；另有独立启动接缝反例。原始输出、HTTP、真实截图及方法边界见[A8 报告](../../vnext/first-use/A8/final-candidate/README.md)。`f957a46` 修复合同资料和启动恢复；不改写基线失败，不因主代理定向检查通过就标独立通过。后续 Sol/xhigh 负责针对修复的独立复核，不再重跑整套 Python。

![固定候选独立检查截图](../../vnext/first-use/A8/final-candidate/screenshots/fixed-candidate-results.png)

[完整脱敏 HTTP 报文](../../vnext/first-use/A8/final-candidate/http-reproduction.md)。该证据只覆盖报告明确列出的服务/记录型边界；不代表 Kubernetes、DeepSeek 或现场端到端通过。

2026-09-19 后续：Sol/xhigh 在 `ef8d462`（生产修复 `f957a46`）独立定向重验：合同 59 passed、接缝最终轮 5 passed，均 exit 0；首轮测试桩缺 namespace 的 2 failed 保留。[重验报告和 HTTP](../../vnext/first-use/A8/recheck-20260919/README.md)。报告原附 SVG 派生 PNG 不是验证截图，A0 已明确纠正为辅助可视化，截图缺项尚未关闭。

历史发布阻塞（2026-09-19 清理前，非用户配置缺失）：本机数据卷在镜像发布期间只余 158 MiB，截图工具同时报 `No space left on device`；移除本轮三个已合并且干净的临时工作树后恢复至约 791 MiB，分支/提交/证据均保留。新 LiteLLM 持久客户端镜像已构建，非 root 只读根文件系统下 Prisma 导入与版本命令通过；当时本地 registry 推送 exit 1 / HTTP 500，无 RepoDigest，未部署。入口 CLI 当时显式阻断旧的不含 Prisma 镜像。[镜像状态及后续记录](../../../ops/vnext/images/litellm-freeze-20260919.json)。内置浏览器补采本机报告页面另被 `ERR_BLOCKED_BY_CLIENT` 拒绝，未绕过。

上述历史截面仅新增部署了命名空间内无凭据的 F1/F2 fixture（ConfigMap/Deployment/ClusterIP/无出口 NetworkPolicy；策略是否由当前 CNI 强制执行尚未验证）。

2026-09-19 继续部署：用户批准清理未使用构建缓存并重启 Docker，磁盘阻塞解除（约25 GiB可用），未删除镜像/容器/数据卷。仓库 VM-loopback 端口从56615变为55529；已有 LiteLLM 镜像重推 exit0，固定 digest `f6bd15c3e189ae2f4c8215f0233770e76c3cf1f94b3a3582877add2dde18ff24`。实际启动发现并定向处理2Gi OOM、Prisma根证书参数和叶证书AKI缺失；SQL迁移已执行到独立网关数据库，严格 HTTPS readiness 在13:14:34 UTC返回200、`{"status":"healthy","db":"connected"}`。本轮网关脚本定向测试最近一次6 passed / exit0，未重跑完整套件。仍存在Prisma0.15初连适配错误，兼容版本构建中；不能用readiness替代预算/模型/首用验收。

当前平台标准构建在GHCR uv层下载约366秒持续0字节后由A0中断，命令exit1及原日志保留于 `work/vnext/k8s/build-fe6_k5hy/`；未安装或运行旧核心代替新实现。新增网关部署不等于整个平台发布：0029仍未上Wuji数据库，旧工作台未滚动，没有创建执行Task、真实模型调用或现场请求。用户已将现场替换为 `http://39.102.208.182`，见[授权记录](../../vnext/first-use/authorization.md)。网关补充截图采集被应用安全限制拒绝，缺项如实保留，不生成替代截图；本段为实施日志，不是已满足双证据的验收成果。
