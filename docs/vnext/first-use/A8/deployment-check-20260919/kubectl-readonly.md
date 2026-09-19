# 2026-09-19 Kubernetes 只读证据

本文件记录实际只读命令、结果和退出码。未读取任何 Secret data；`get secret` 仅使用 `-o name`。主树发布清单独立读取自 `/Users/yym1ng/Documents/ChatGPT/wuji/work/worktrees/vnext-maf/work/vnext/k8s/publish-hn_of44m/images-published.json`：core source revision `af36be86c3aedc20f11fcfd5e1d2853ecf1c66ea`，platform digest `sha256:85ed686f0e802b015c851f591db938863138430329ff1f6176e57c714849f56b`，agent digest `sha256:830b146e875c0489597b957daffbc8ee62ec9a4def61c6184be0c36d8a3e1444`，kali digest `sha256:6e2d52a5fa55c24df58a3c4490376f58618d7dc46efa8b1e8ae56c8a2dcc038e`。

## 上下文

命令 `kubectl config current-context` 返回 `docker-desktop`，exit `0`。

## 七个首用入口 Deployment

命令：`kubectl get deployment -n wuji-vnext-test -o json | jq -S '[.items[] | select(.metadata.name as $n | (["api","runtime","scheduler","gates","first-use-launch","first-use-fixture","wuji-web"] | index($n))) | {name:.metadata.name,uid:.metadata.uid,desiredReplicas:(.spec.replicas // 0),readyReplicas:(.status.readyReplicas // 0),availableReplicas:(.status.availableReplicas // 0),availableCondition:([.status.conditions[]? | select(.type=="Available") | {status,reason,message}] | first),serviceAccountName:(.spec.template.spec.serviceAccountName // "default"),containers:[.spec.template.spec.containers[] | {name,image}]}]'`，exit `0`。

七项均 `desired/ready/available=1/1/1`，`Available=True / MinimumReplicasAvailable`：

| Deployment | serviceAccount | containers and image |
| --- | --- | --- |
| `api` | `default` | `api`: `127.0.0.1:55529/wuji-vnext-platform@sha256:85ed686f0e802b015c851f591db938863138430329ff1f6176e57c714849f56b` |
| `first-use-fixture` | `default` | `fixture`: platform digest above |
| `first-use-launch` | `first-use-launch` | `launch`: platform digest above |
| `gates` | `first-use-gates` | `gates` + `synthetic-model`: platform digest above |
| `runtime` | `runtime` | `runtime`: platform digest above |
| `scheduler` | `default` | `scheduler`: platform digest above |
| `wuji-web` | `default` | `web`: `127.0.0.1:55529/wuji-web@sha256:e84b4f467ea1ce5f12c1f761e0662844fe6b8e2021be8ec98f3b25242cd02925`; `gateway`: platform digest above |

## 七个入口 Pod 的实际 imageID

命令：`kubectl get pod -n wuji-vnext-test -o json | jq -S '[.items[] | select(.metadata.name | test("^(api|runtime|scheduler|gates|first-use-launch|first-use-fixture|wuji-web)-")) | {name:.metadata.name,uid:.metadata.uid,phase:.status.phase,ready:([.status.conditions[]? | select(.type=="Ready") | {status,reason,message}] | first),containers:[.status.containerStatuses[]? | {name,image,imageID,ready,started,restartCount}]}]'`，exit `0`。

所有匹配 Pod 均 `Running`、Ready `True`；实际 Pod name 为 `api-688dc8f69f-mgjsm`、`first-use-fixture-79d57fb994-lnnv2`、`first-use-launch-769f9785fd-msrgl`、`gates-d864597d8-fwjwd`、`runtime-7d87884d4d-4qmgz`、`scheduler-8676dbf4f7-zp62k`、`wuji-web-595fbf6f57-x4k8f`。

所有平台容器实际 `imageID` 均为 `docker-pullable://127.0.0.1:55529/wuji-vnext-platform@sha256:85ed686f0e802b015c851f591db938863138430329ff1f6176e57c714849f56b`；`gates` 两容器均匹配；`wuji-web` gateway 匹配。`wuji-web` web 容器实际 `imageID` 为 `docker-pullable://127.0.0.1:55529/wuji-web@sha256:e84b4f467ea1ce5f12c1f761e0662844fe6b8e2021be8ec98f3b25242cd02925`。

## 独立 LiteLLM

命令 `kubectl get deployment first-use-litellm -n wuji-first-use-model -o json | jq ...` 与 `kubectl get pod -n wuji-first-use-model -o json | jq ...` 均 exit `0`。Deployment `wuji-first-use-model/first-use-litellm` 为 `desired/ready/available=1/1/1`、`Available=True`，image 为 `127.0.0.1:55529/wuji-first-use-litellm@sha256:11c59c67f03f4012d9000d210147ace1e0058144962d2301db916517c4494c1d`；Pod `first-use-litellm-dc47bc986-k6dgk` 为 `Running`、Ready `True`，实际 imageID 为 `docker-pullable://127.0.0.1:55529/wuji-first-use-litellm@sha256:11c59c67f03f4012d9000d210147ace1e0058144962d2301db916517c4494c1d`。

## 相关 Job

命令 `kubectl get job -n wuji-vnext-test -o json | jq -S '[.items[] | select(.metadata.name | test("first-use|catalog")) | {name:.metadata.name,uid:.metadata.uid,completions:.spec.completions,active:(.status.active // 0),succeeded:(.status.succeeded // 0),failed:(.status.failed // 0),conditions:([.status.conditions[]? | {type,status,reason,message}]),containers:[.spec.template.spec.containers[]? | {name,image}]}]'`，exit `0`。`first-use-catalog-mechanism-af36be86-5efb0f49` 为 `succeeded=1, failed=0, Complete=True`，使用 platform digest；历史 `first-use-catalog-mechanism-d390585ff9` 与 `first-use-catalog-mechanism-d3afb4dbb2` 各为 `failed=1, BackoffLimitExceeded`，实际旧镜像 digest 分别为 `sha256:f4b08378deb134fb9f840d6d92ab906d43f1c2b54af40a68188cb392fce6b25`、`sha256:82fb251fa369626779ebb742f4da10a0fae5fa40266dde4f1a455e4b739d034e`。`wuji-first-use-model` 同筛选结果为 `[]`，exit `0`。

## 旧资源与 RBAC 隔离

- 命令 `kubectl get deployment first-use-litellm -n wuji-vnext-test -o json | jq ...`，exit `0`：`desiredReplicas=0, readyReplicas=0, availableReplicas=0`。
- 命令 `kubectl get pod -n wuji-vnext-test -o json | jq '[.items[] | select(.metadata.name | startswith("first-use-litellm-"))]'`，exit `0`：结果 `[]`。
- 命令 `kubectl get secret deepseek-provider-first-use -n wuji-vnext-test -o name`，exit `1`：`Error from server (NotFound): secrets "deepseek-provider-first-use" not found`。
- 命令 `kubectl get secret deepseek-provider-first-use -n wuji-first-use-model -o name`，exit `0`：`secret/deepseek-provider-first-use`。
- 命令 `kubectl auth can-i get secret/deepseek-provider-first-use -n wuji-first-use-model --as=system:serviceaccount:wuji-vnext-test:first-use-launch`，exit `1`：`no`。

上述 Secret 命令没有读取 data；`auth can-i` 只验证授权结果。历史 C2/非首用 Job/Pod 未作为七个入口的就绪结论。
