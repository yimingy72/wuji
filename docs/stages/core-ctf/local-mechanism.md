# Core CTF 本地机制运行

状态：入口已实现，完整运行结果以[验收](acceptance.md)为准。仅使用本地合成模型与独立靶标；不证明真实模型CTF效果，也不向旧`wuji-vnext-test`应用资源。

## 1. 固定源码与输入

在检出`codex/vnext-maf`的工作树操作。先核对`git status`、提交SHA和镜像源码标签；业务镜像必须来自同一固定源码。准备私有ignored目录和密码摘要：

```sh
mkdir -p work/core-ctf/local-run
chmod 700 work/core-ctf/local-run
./scripts/vnext/uv.sh run --frozen python scripts/vnext/set_web_password.py \
  --username operator --output "$PWD/work/core-ctf/local-run/password.json"
```

该命令通过隐藏输入读取密码。不要复用参考平台账号凭据。`images.json`包含`platform/agent/kali/capture/web/postgres`六项，每项是`{"reference":"仓库@sha256:完整摘要","source_revision":"实际源码SHA"}`；PostgreSQL不要求业务源码SHA。platform/agent/kali使用`ops/vnext/images/Dockerfile`对应target，capture使用`Dockerfile.capture`，web使用`apps/web/Dockerfile`。本地工具二进制缓存只用于相同版本uv/Node，不复用旧业务层冒称新代码。

## 2. 渲染并检查

```sh
./scripts/vnext/uv.sh run --frozen python scripts/vnext/core_ctf_platform.py \
  --state-directory "$PWD/work/core-ctf/local-run" \
  --images "$PWD/work/core-ctf/local-run/images.json" \
  --namespace wuji-core-ctf --architecture arm64 --web-port 44181 \
  --explore-limit 4 --pool-capacity 5 \
  --password-credential "$PWD/work/core-ctf/local-run/password.json"
```

4/5仅为这个本地环境显式选定的容量；平台没有固定“两名Explore”的规则。Task可以选择发布上限内的并发，Reason仍与Explore共享全局容量。

渲染只写文件，不部署、不创建Task、不调用模型。`configuration/`内含私有Secret，不能提交Git或打印整份JSON；`public.json`可以核对namespace、浏览器入口和本地靶标。首次部署前检查每个资源都属于该独立namespace，确认没有旧实例的数据库、PVC或身份引用。

## 3. 本地部署顺序

确认Docker Desktop为当前本地集群，按`public.json.apply_order`部署：

```sh
kubectl --context docker-desktop apply -f work/core-ctf/local-run/configuration/foundation.json
kubectl --context docker-desktop -n wuji-core-ctf rollout status deployment/postgres --timeout=60s
kubectl --context docker-desktop apply -f work/core-ctf/local-run/configuration/bootstrap-job.json
kubectl --context docker-desktop -n wuji-core-ctf wait --for=condition=complete job/core-bootstrap --timeout=60s
kubectl --context docker-desktop apply -f work/core-ctf/local-run/configuration/catalog-job.json
kubectl --context docker-desktop -n wuji-core-ctf wait --for=condition=complete job/core-catalog --timeout=60s
kubectl --context docker-desktop apply -f work/core-ctf/local-run/configuration/platform.json
kubectl --context docker-desktop -n wuji-core-ctf get pods
```

超时先看对应Job/Pod日志定位，不盲目重建数据库或重新生成身份。平台初始为空项目，无占位执行Task。浏览器入口为`http://127.0.0.1:44181/`；会话存在该环境自己的PVC中。

## 4. 机制链与浏览器

在私有`run.json`中填写以下字段（实际文件权限0600）：

```json
{
  "schema_version": "wuji.core-ctf-run.v1",
  "mode": "mechanism",
  "run_id": "core-mechanism-unique-id",
  "configuration_directory": "/绝对工作树/work/core-ctf/local-run/configuration",
  "evidence_directory": "/绝对工作树/work/core-ctf/local-run/evidence",
  "expected_source_revision": "实际源码SHA",
  "username": "operator",
  "password": "仅私有运行文件填写",
  "timeout_seconds": 600,
  "poll_seconds": 1,
  "task": {
    "name": "Core CTF 本地协作验证",
    "goal": "访问获准本地入口，保存响应并通过固定脚本版本完成A/B交接",
    "criteria": ["B复用A发布的固定脚本，响应状态与正文摘要可由独立采集核对"],
    "authorization_expires_at": "实际有效的UTC截止时间",
    "budget_amount": "1",
    "model_profile_ref": "core-ctf-mechanism-model-v1",
    "runtime_profile_ref": "core-ctf-runtime-v1",
    "explore_concurrency": 4
  }
}
```

先检查输入，再运行一次：

```sh
./scripts/vnext/uv.sh run --frozen python tests/vnext/run_core_ctf.py \
  --mode mechanism --run-file "$PWD/work/core-ctf/local-run/run.json" --validate-only
./scripts/vnext/uv.sh run --frozen python tests/vnext/run_core_ctf.py \
  --mode mechanism --run-file "$PWD/work/core-ctf/local-run/run.json"
```

入口核对创建后零执行，再显式启动。保存A/B发布manifest、脚本、真实命令日志、HTTP各part、最终PCAP/manifest和四容器外部终态。`Task.closed`和capture sealed均不单独充当容器退出证据；取消后的执行停止与业务结果结算分别记录。失败保留`failure.json`与原始请求响应，不重复未知命令。

浏览器在同一真实环境检查登录、两个并存会话、任务切换、活动筛选、共享版本、命令/HTTP/PCAP下钻及停止状态，截图写入证据目录`screenshots/`。仅运行脚本、只看Pod Ready或通过纯逻辑测试都不算完整验收。真实模型与外部题目另需有效授权，本入口没有自动切换真实模式。
