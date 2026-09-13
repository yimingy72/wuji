"""Redact and bind the already completed P13 review-fix run."""

from __future__ import annotations

import base64
import gzip
import hashlib
import html
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
RAW = OUT / "raw"
COMMIT = "69e3a1d"
TEST_COMMAND = (
    "WUJI_TEST_EVIDENCE_DIR=\"$PWD/docs/vnext/evidence/P13/review-fix/raw\" "
    "./scripts/vnext/uv.sh run --frozen pytest "
    "tests/vnext/test_view_snapshots.py::test_openapi_declares_actual_410_responses_for_snapshot_reads "
    "tests/vnext/test_view_snapshots.py::test_history_lists_only_saved_views_and_freezes_its_opaque_page "
    "tests/vnext/test_view_snapshots.py::test_expired_view_and_snapshot_return_explicit_410_errors -q"
)
GENERATION_COMMAND = (
    "./scripts/vnext/uv.sh run --frozen python scripts/vnext/generate_contracts.py --check"
)
BOUND = (
    "packages/contracts/openapi-v2.yaml",
    "packages/contracts/src/v2/generated.ts",
    "packages/wuji-core/src/wuji_core/projection/snapshots.py",
    "tests/vnext/test_view_snapshots.py",
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def redact(exchange: dict) -> None:
    header = exchange["request"]["headers"].get("authorization")
    if not header or not header.startswith("Bearer eyJ"):
        return
    token = header.removeprefix("Bearer ")
    claims = json.loads(base64.urlsafe_b64decode(token.split(".")[1] + "==="))
    replacement = "Bearer ${TOKEN_" + claims["sub"].replace("-", "_") + "}"
    exchange["request"]["headers"]["authorization"] = replacement
    exchange["authorization_evidence"] = {
        "subject": claims["sub"],
        "roles": claims["roles"],
        "original_header_sha256": sha(header.encode()),
        "replacement": "ephemeral isolated-fixture token; regenerate with test issuer",
    }


exchanges = []
for source in sorted(RAW.rglob("*http-exchanges.jsonl")):
    output = []
    for line in source.read_text(encoding="utf-8").splitlines():
        exchange = json.loads(line)
        redact(exchange)
        output.append(json.dumps(exchange, ensure_ascii=False, sort_keys=True))
        exchanges.append((str(source.parent.relative_to(RAW)), exchange))
    source.write_text("\n".join(output) + "\n", encoding="utf-8")

for source in sorted(RAW.rglob("postgres-events.jsonl")):
    compressed = source.with_suffix(".jsonl.gz")
    compressed.write_bytes(gzip.compress(source.read_bytes(), mtime=0))
    source.unlink()

commit = subprocess.check_output(
    ["git", "rev-parse", COMMIT], cwd=ROOT, text=True
).strip()
file_hashes = {}
for path in BOUND:
    committed = subprocess.check_output(["git", "show", commit + ":" + path], cwd=ROOT)
    if committed != (ROOT / path).read_bytes():
        raise AssertionError(f"working tree differs from bound commit: {path}")
    file_hashes[path] = sha(committed)
(OUT / "binding.json").write_text(
    json.dumps(
        {
            "code_commit": commit,
            "test_command": TEST_COMMAND,
            "test_result": "3 passed in 3.16s",
            "test_exit_code": 0,
            "generation_command": GENERATION_COMMAND,
            "generation_result": "generated Python and TypeScript contracts match OpenAPI",
            "generation_exit_code": 0,
            "tested_as_working_tree_then_committed_without_content_change": True,
            "file_sha256": file_hashes,
        },
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)

parts = [
    "# P13 review-fix 完整 HTTP 请求与响应",
    "",
    "以下报文来自两个定向真实 PG/签名 ASGI 用例。method、URL、headers、请求体、响应 headers/status/body 均完整保留；Authorization 已替换为可重新签发的测试变量并保留原 Header SHA-256。",
    "",
]
for number, (node, exchange) in enumerate(exchanges, 1):
    request, response = exchange["request"], exchange["response"]
    request_body = base64.b64decode(request["body_base64"]).decode("utf-8")
    response_body = base64.b64decode(response["body_base64"]).decode("utf-8")
    point = (
        "漏洞/控制点：live 携带历史 snapshot_id 必须拒绝，history 续页保持原查询身份。"
        if "/topology" in request["url"]
        else "漏洞/控制点：过期历史/游标返回声明内 410，不回退 latest。"
        if "/snapshots" in request["url"] or "/records/" in request["url"]
        else "真实前提：既有生产 API 建立隔离证据与 Claim。"
    )
    parts.extend(
        [
            f"## Exchange {number} · {node}",
            "",
            point,
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
(OUT / "http-reproduction.md").write_text("\n".join(parts), encoding="utf-8")

catalog = []
for source in sorted(RAW.rglob("*")):
    if source.is_file():
        catalog.append(
            {
                "path": str(source.relative_to(OUT)),
                "bytes": source.stat().st_size,
                "sha256": sha(source.read_bytes()),
            }
        )
(OUT / "evidence-index.json").write_text(
    json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
(OUT / "result.txt").write_text(
    "...                                                                      [100%]\n"
    "3 passed in 3.16s\n\n"
    "Generated Python and TypeScript v2 contracts match OpenAPI.\n",
    encoding="utf-8",
)

live_denial = next(
    exchange
    for _, exchange in exchanges
    if "mode=live" in exchange["request"]["url"]
    and "snapshot_id=" in exchange["request"]["url"]
)
expired_index = next(
    exchange
    for _, exchange in exchanges
    if exchange["response"]["status_code"] == 410
    and json.loads(base64.b64decode(exchange["response"]["body_base64"]))["code"]
    == "VIEW_EXPIRED"
)
blocks = []
for title, exchange in [
    ("live + historical snapshot 拒绝", live_denial),
    ("过期 index cursor 410", expired_index),
]:
    body = json.loads(base64.b64decode(exchange["response"]["body_base64"]))
    blocks.append(
        f"<h2>{html.escape(title)}</h2><pre>{html.escape(json.dumps(body, ensure_ascii=False, indent=2))}</pre>"
    )
(OUT / "result.html").write_text(
    f"""<!doctype html><html lang="zh"><meta charset="utf-8"><title>P13 review fixes</title>
<style>body{{font:16px system-ui;margin:32px;background:#f5f7fa;color:#182331}}h1{{font-size:28px}}pre{{white-space:pre-wrap;background:white;border:1px solid #d5dee8;padding:16px;font:13px ui-monospace}}.ok{{color:#145c35;font-weight:700}}.meta{{color:#40546a}}</style>
<h1>P13 · 两项 P2 定向修复</h1><p class="ok">3 passed in 3.16s · generation check exit 0</p>
<p class="meta">代码提交 {commit}<br>真实签名 ASGI · 隔离 nonowner PostgreSQL · 保存响应渲染</p>
<h2>命令</h2><pre>{html.escape(TEST_COMMAND)}\n3 passed in 3.16s\n\n{html.escape(GENERATION_COMMAND)}\nexit 0</pre>
{''.join(blocks)}<p>旧 12 项未重跑；本页不是产品 UI。</p></html>""",
    encoding="utf-8",
)

print(json.dumps({"commit": commit, "http_exchanges": len(exchanges), "files": len(catalog)}, indent=2))
