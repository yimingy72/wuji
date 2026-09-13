"""Package an already completed P13 run without rerunning PostgreSQL or HTTP."""

from __future__ import annotations

import base64
import gzip
import hashlib
import html
import json
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
COMMIT = "44ddc68"
COMMAND = "./scripts/vnext/uv.sh run --frozen pytest tests/vnext/test_view_snapshots.py -q"
RESULT = "............                                                             [100%]\n12 passed in 8.16s\n"
BOUND_PATHS = (
    "packages/wuji-core/src/wuji_core/blackboard/fact_view.py",
    "packages/wuji-core/src/wuji_core/http/topology.py",
    "packages/wuji-core/src/wuji_core/persistence/projection_schema.py",
    "packages/wuji-core/src/wuji_core/persistence/schema.py",
    "packages/wuji-core/src/wuji_core/projection/access.py",
    "packages/wuji-core/src/wuji_core/projection/records.py",
    "packages/wuji-core/src/wuji_core/projection/snapshots.py",
    "tests/vnext/support/p13.py",
    "tests/vnext/test_view_snapshots.py",
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def redact_authorization(exchange: dict) -> None:
    authorization = exchange["request"]["headers"].get("authorization")
    if not authorization:
        return
    token = authorization.removeprefix("Bearer ")
    claims = json.loads(base64.urlsafe_b64decode(token.split(".")[1] + "==="))
    subject = claims["sub"]
    exchange["request"]["headers"]["authorization"] = (
        "Bearer ${TOKEN_" + subject.replace("-", "_") + "}"
    )
    exchange["authorization_evidence"] = {
        "subject": subject,
        "roles": claims["roles"],
        "original_header_sha256": digest(authorization.encode()),
        "replacement": "ephemeral isolated-fixture token; regenerate with test issuer",
    }


def control_point(method: str, url: str, status: int) -> str:
    if "/topology" in url and "cursor=" in url and status == 404:
        return "漏洞/控制点：旧视图或错误主体/查询不能复用 opaque cursor。"
    if "/topology" in url:
        return "漏洞/控制点：固定 snapshot 分页，隐藏数据与内部序号不得进入公开图。"
    if "/snapshots" in url:
        return "漏洞/控制点：只列真实保存且当前可访问的历史，索引页保持冻结。"
    if "/records/" in url:
        return "漏洞/控制点：详情读取当前重验权限，并从保存版本读取固定正文。"
    if status in {401, 403, 404, 410, 422}:
        return "漏洞/控制点：负向请求由统一错误合同拒绝，不回退到假许可或 latest。"
    if method == "POST":
        return "真实前提：通过既有生产 API 建立证据、Claim 或评估，不是 fake 服务。"
    return "真实前提/控制点：隔离签名请求与实际响应完整保留。"


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: package-evidence.py PYTEST_RAW_ROOT")
    raw_root = Path(sys.argv[1]).resolve()
    if not raw_root.is_dir():
        raise SystemExit(f"missing raw root: {raw_root}")

    runtime = OUT / "runtime"
    if runtime.exists():
        shutil.rmtree(runtime)
    runtime.mkdir(parents=True)
    exchanges: list[tuple[str, dict]] = []
    catalog = []
    for source in sorted(raw_root.rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(raw_root)
        destination = runtime / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        original = source.read_bytes()
        if source.name.endswith("http-exchanges.jsonl"):
            lines = []
            for line in original.decode().splitlines():
                exchange = json.loads(line)
                redact_authorization(exchange)
                lines.append(json.dumps(exchange, ensure_ascii=False, sort_keys=True))
                exchanges.append((str(relative.parent), exchange))
            destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
        elif source.name == "postgres-events.jsonl":
            destination = destination.with_suffix(".jsonl.gz")
            destination.write_bytes(gzip.compress(original, mtime=0))
        else:
            shutil.copyfile(source, destination)
        catalog.append(
            {
                "path": str(destination.relative_to(OUT)),
                "sha256": digest(destination.read_bytes()),
                "original_sha256": digest(original),
                "original_bytes": len(original),
            }
        )

    bindings = {}
    for path in BOUND_PATHS:
        data = subprocess.check_output(
            ["git", "show", COMMIT + ":" + path], cwd=ROOT
        )
        bindings[path] = digest(data)
        current = (ROOT / path).read_bytes()
        if current != data:
            raise AssertionError(f"working tree differs from bound commit: {path}")
    binding = {
        "code_commit": subprocess.check_output(
            ["git", "rev-parse", COMMIT], cwd=ROOT, text=True
        ).strip(),
        "tested_as_working_tree_then_committed_without_content_change": True,
        "command": COMMAND,
        "exit_code": 0,
        "result": "12 passed in 8.16s",
        "file_sha256": bindings,
    }
    (OUT / "binding.json").write_text(
        json.dumps(binding, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "evidence-index.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "result.txt").write_text(RESULT, encoding="utf-8")

    parts = [
        "# P13 完整夹具 HTTP 请求与响应",
        "",
        "以下报文来自真实签名 ASGI 路由与隔离 nonowner PostgreSQL 运行。请求方法、URL、Headers、请求体、响应状态、Headers 与响应体均完整保留；body 同时保存在 runtime JSONL 的原始 base64 字节中。Authorization 替换为可重新签发的测试变量，并保留原 Header SHA-256；未提交 bearer 或私钥。",
        "",
        f"复现命令：`{COMMAND}`。输入实现绑定见 `binding.json`。`http://testserver` 是真实 ASGI transport 的测试 authority；没有外部目标、收费模型或生产流量。",
        "",
    ]
    for index, (node, exchange) in enumerate(exchanges, 1):
        request = exchange["request"]
        response = exchange["response"]
        request_body = base64.b64decode(request["body_base64"]).decode("utf-8")
        response_body = base64.b64decode(response["body_base64"]).decode("utf-8")
        parts.extend(
            [
                f"## Exchange {index} · {node}",
                "",
                control_point(request["method"], request["url"], response["status_code"]),
                "",
                "```http",
                f"{request['method']} {request['url']} HTTP/1.1",
                *(f"{key}: {value}" for key, value in request["headers"].items()),
                "",
                request_body,
                "```",
                "",
                "```http",
                f"HTTP/1.1 {response['status_code']}",
                *(f"{key}: {value}" for key, value in response["headers"].items()),
                "",
                response_body,
                "```",
                "",
            ]
        )
    (OUT / "http-reproduction.md").write_text(
        "\n".join(parts), encoding="utf-8"
    )

    topology_ok = next(
        exchange
        for _, exchange in exchanges
        if "/topology" in exchange["request"]["url"]
        and exchange["response"]["status_code"] == 200
    )
    denial = next(
        exchange
        for _, exchange in exchanges
        if exchange["response"]["status_code"] in {404, 410}
    )
    run_record = next(
        exchange
        for _, exchange in exchanges
        if "/records/agent_run/" in exchange["request"]["url"]
        and exchange["response"]["status_code"] == 200
    )
    shown = [
        ("固定拓扑页", topology_ok),
        ("当前权限/历史拒绝", denial),
        ("真实来源 Run 详情", run_record),
    ]
    blocks = []
    for title, exchange in shown:
        body = json.loads(base64.b64decode(exchange["response"]["body_base64"]))
        blocks.append(
            f"<h2>{html.escape(title)}</h2><pre>{html.escape(json.dumps(body, ensure_ascii=False, indent=2))}</pre>"
        )
    result_html = f"""<!doctype html><html lang="zh"><meta charset="utf-8">
<title>P13 persistent projection verification</title>
<style>body{{font:16px system-ui;margin:32px;background:#f5f7fa;color:#182331}}h1{{font-size:28px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:white;border:1px solid #d5dee8;padding:16px;font:13px ui-monospace}}.ok{{color:#145c35;font-weight:700}}.meta{{color:#40546a}}</style>
<h1>P13 · 持久受权投影真实验证</h1>
<p class="ok">12 passed in 8.16s · exit 0</p>
<p class="meta">代码提交 {binding['code_commit']}<br>真实签名 ASGI · 隔离 nonowner PostgreSQL · migration vnext_0012_p13_projection<br>本页渲染已保存响应，不是产品 UI，也未触发新的数据库或 HTTP 请求。</p>
<h2>聚合命令</h2><pre>{html.escape(COMMAND)}\n{html.escape(RESULT)}</pre>
{''.join(blocks)}
<p>覆盖固定分页/详情、历史、当前权限、隐藏依据、opaque cursor、无执行、同 RR FactLedger、safe-field Run 来源。Layout/stream/P14 正式容器不在本次后端通过范围。</p>
</html>"""
    (OUT / "result.html").write_text(result_html, encoding="utf-8")
    print(
        json.dumps(
            {
                "code_commit": binding["code_commit"],
                "http_exchanges": len(exchanges),
                "runtime_files": len(catalog),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
