# A8 限定独立部署入口复核

结论：本报告仅覆盖 2026-09-19 的部署入口、镜像绑定、旧网关隔离和未认证 HTTP 边界；范围内通过。它不等同于完整 A8、DG1、DG2 或 DG3 通过。

## 执行边界

- 执行者：A8 子代理 Banach（`gpt-5.6-luna/xhigh`），相对本轮实现独立；未再派发子代理，未读取浏览器现有 session。A0集成时依据实际派发记录纠正原稿误写的“主代理”，不改变原始检查结果。
- 工作树：`/Users/yym1ng/Documents/ChatGPT/wuji/work/worktrees/first-use-entry-review`。
- 被核对代码 HEAD：`a28c887d82660c9e0e66fc563d37e785c48f10be`；执行时工作树无未提交变更。
- 集群上下文：`docker-desktop`。只读 `kubectl get Deployment/Pod/Job` 的元数据、镜像和就绪信息，以及指定 Secret 的存在性和 `auth can-i`；没有读取 Secret data，也没有操作集群。
- 主树发布清单：`/Users/yym1ng/Documents/ChatGPT/wuji/work/worktrees/vnext-maf/work/vnext/k8s/publish-hn_of44m/images-published.json`，独立读取并用于下表对照。
- 主树证据提交：`f24df0a`。下方截图从该提交的现有文件复制到本目录；它是 A0 实际 CUA 截图，不是本次复核捕获，也不冒称为本次截图。

![A0 实际 CUA 工作台登录截图（复制自主树 f24df0a）](screenshots/workbench-login.png)

完整 HTTP 请求/响应见 [http-reproduction.md](http-reproduction.md)；完整只读命令、JSON 结果和退出码见 [kubectl-readonly.md](kubectl-readonly.md)。

## 结果摘要

| 检查 | 实际结果 | 判定 |
| --- | --- | --- |
| `GET /` | `200 OK`，完整 HTML 正文已记录 | 通过 |
| 未认证 `GET /auth/session` | `401`，`UNAUTHENTICATED` | 通过 |
| `Host: unapproved.invalid` 的 `GET /auth/session` | `400`，`INVALID_SCHEMA` | 通过 |
| 无 Cookie/访问码且仅 `Origin: http://unapproved.invalid` 的 `POST /auth/login` | `403`，`FORBIDDEN` | 通过 |
| 七个首用入口 Deployment/Pod | 7/7 Deployment `1/1 Ready`；对应 Pod 均 `Running` 且 `Ready=True`；实际 `imageID` 已逐项记录 | 通过 |
| 独立 LiteLLM | `wuji-first-use-model/first-use-litellm` 为 `1/1 Ready`，Pod `Ready=True` | 通过 |
| 旧 provider Secret | `wuji-vnext-test/deepseek-provider-first-use` 不存在（`kubectl get` exit 1） | 通过 |
| 新 provider Secret | `wuji-first-use-model/deepseek-provider-first-use` 仅核对存在（exit 0），未读取内容 | 通过 |
| `first-use-launch` 跨 namespace 读 provider | `kubectl auth can-i ...` 返回 `no`（exit 1） | 通过 |
| 旧 `first-use-litellm` | `wuji-vnext-test` Deployment replicas `0`、ready `0`，匹配 Pod 为 `[]` | 通过 |

## 镜像 code binding

主树 `images-published.json` 的核心 source revision 为 `af36be86c3aedc20f11fcfd5e1d2853ecf1c66ea`。七个首用入口 Deployment 使用 platform 镜像，Pod 实际 `imageID` 均为清单中的 platform digest：

| 组件/用途 | 绑定信息 | 实际核对 |
| --- | --- | --- |
| API、fixture、launch、gates、runtime、scheduler、Web gateway | `127.0.0.1:55529/wuji-vnext-platform@sha256:85ed686f0e802b015c851f591db938863138430329ff1f6176e57c714849f56b`；source revision `af36be86…` | 七个入口 Deployment/Pod 均匹配该 digest |
| Web 静态容器 | payload `5cdbd170939f1d2e410868ab591381331f5cdba9`，另加 Nginx Host/config 修复；`127.0.0.1:55529/wuji-web@sha256:e84b4f467ea1ce5f12c1f761e0662844fe6b8e2021be8ec98f3b25242cd02925` | `wuji-web` 的 `web` 容器 Deployment/Pod 均匹配；不是声称整张 `5cdbd17` 镜像未变 |
| 独立 LiteLLM | `127.0.0.1:55529/wuji-first-use-litellm@sha256:11c59c67f03f4012d9000d210147ace1e0058144962d2301db916517c4494c1d` | 新 namespace Deployment/Pod 均匹配 |
| 清单中未由本轮新 Task 启动的镜像 | agent digest `sha256:830b146e875c0489597b957daffbc8ee62ec9a4def61c6184be0c36d8a3e1444`；kali digest `sha256:6e2d52a5fa55c24df58a3c4490376f58618d7dc46efa8b1e8ae56c8a2dcc038e` | 本轮无新 Task，未把它们冒称为运行中 Task Pod 证据 |

## 限制与未覆盖项

用户尚未填写原生日期，当前没有新 Task；本轮没有登录、没有使用访问码、没有创建/启动 Task、没有调用真实模型，也没有访问 `http://39.102.208.182`。因此本报告不声称 Task/DG1、DeepSeek/DG2、现场/DG3、预算、真实模型、工具往返、暂停取消或现场通过。

历史 C2/旧 Job/失败 Job 保留在集群中；本报告只将成功的首用 catalog Job 记录为当前发布辅助证据，并把两份历史失败 Job 如实列为历史保留，未把它们改写为通过。旧网关和 provider 隔离只覆盖本报告列出的资源与 RBAC 断言。
