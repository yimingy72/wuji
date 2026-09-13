import { mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import { basename, join } from "node:path";

const evidenceRoot = process.argv[2];
if (!evidenceRoot) {
  throw new Error("usage: node build-supervisor-evidence.mjs EVIDENCE_ROOT");
}
const coreSha = process.env.WUJI_P10_CORE_SHA;
const testSha = process.env.WUJI_P10_TEST_SHA;
if (!/^[a-f0-9]{40}$/.test(coreSha ?? "") || !/^[a-f0-9]{40}$/.test(testSha ?? "")) {
  throw new Error("WUJI_P10_CORE_SHA and WUJI_P10_TEST_SHA must be full Git SHAs");
}

const rawDirectory = join(evidenceRoot, "raw");
const records = [];
for (const name of (await readdir(rawDirectory)).filter((name) => name.endsWith(".json")).sort()) {
  records.push({ name, body: JSON.parse(await readFile(join(rawDirectory, name), "utf8")) });
}

const junit = await readFile(join(evidenceRoot, "node-junit.xml"), "utf8");
const metric = (name) => Number(junit.match(new RegExp(`<!-- ${name} ([0-9.]+) -->`))?.[1]);
const summary = {
  tests: metric("tests"),
  pass: metric("pass"),
  fail: metric("fail"),
  duration_ms: metric("duration_ms"),
};

const issueByLabel = {
  "before-prepared": "prepared 前崩溃不能留下伪执行事实；原 operation 可重新派发且实际只出生一次。",
  "prepared-before-spawn": "prepared 已持久化但无可信未启动证明时必须 unknown，不能盲目 spawn。",
  "after-spawn-before-running-receipt": "实际出生后、running 回执前崩溃必须恢复同一进程身份，不能双 spawn。",
  "after-running-before-response": "running 已持久化但响应丢失时必须返回原回执，不能双 spawn。",
  "old-runtime": "旧 runtime_attempt 必须在 spawn 前拒绝。",
  "digest-conflict": "同 operation 的不同 Assignment 摘要必须冲突拒绝。",
  "control-exit": "旧 control 身份必须拒绝；accepted 不能冒充 exited。",
};

function fenced(value, language = "json") {
  return `\
\`\`\`${language}\n${value}\n\`\`\``;
}

const http = [
  "# P10 Node Supervisor 完整 HTTP 复现包",
  "",
  `基线：Node core \`${coreSha}\`；测试 \`${testSha}\`。所有地址均为测试进程临时绑定的 \`127.0.0.1\` 端口；Bearer 是固定无权限测试字符串。崩溃窗口的首个 PUT 被真实 \`SIGKILL\` 中断，因此没有 HTTP 响应体，随后 GET/PUT 展示持久恢复结果。`,
  "",
];

for (const { name, body } of records) {
  http.push(`## ${body.label}`, "", `漏洞点/验证点：${issueByLabel[body.label]}`, "");
  body.http_exchanges.forEach((exchange, index) => {
    const url = new URL(exchange.request.url);
    const requestBody = exchange.request.body === null
      ? ""
      : JSON.stringify(exchange.request.body);
    const requestHeaders = {
      Host: url.host,
      ...exchange.request.headers,
    };
    if (requestBody) requestHeaders["Content-Length"] = String(Buffer.byteLength(requestBody));
    const requestLines = [
      `${exchange.request.method} ${url.pathname}${url.search} HTTP/1.1`,
      ...Object.entries(requestHeaders).map(([key, value]) => `${key}: ${value}`),
      "",
      requestBody,
    ];
    http.push(`### 请求/响应 ${index + 1}`, "", fenced(requestLines.join("\n"), "http"), "");
    if (exchange.response) {
      const responseLines = [
        `HTTP/1.1 ${exchange.response.status}`,
        ...Object.entries(exchange.response.headers).map(([key, value]) => `${key}: ${value}`),
        "",
        exchange.response.responseText,
      ];
      http.push(fenced(responseLines.join("\n"), "http"), "");
    } else {
      http.push(
        fenced(
          `<connection closed by injected Supervisor SIGKILL>\n${exchange.error.name}: ${exchange.error.message}`,
          "text",
        ),
        "",
      );
    }
  });
  http.push(
    "实际进程证据：",
    "",
    fenced(JSON.stringify({
      actual_starts: body.actual_starts,
      child_lifecycle: body.child_lifecycle,
      supervisor_crashes: body.supervisor_crashes,
    }, null, 2)),
    "",
  );
}

await writeFile(
  join(evidenceRoot, "http-reproduction.md"),
  `${http.join("\n").trimEnd()}\n`,
);

const rows = records.map(({ body }) => `
  <tr>
    <td>${body.label}</td>
    <td>${body.supervisor_crashes.length}</td>
    <td>${body.actual_starts.length}</td>
    <td>${body.child_lifecycle.filter(({ event }) => event === "birth").length}</td>
    <td>${body.child_lifecycle.filter(({ event }) => event === "exit").length}</td>
    <td>${body.http_exchanges.length}</td>
  </tr>`).join("");
const html = `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>P10 Node Supervisor verification</title>
<style>
body{margin:0;background:#0b1020;color:#e8edf7;font:16px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace}
main{width:1180px;margin:0 auto;padding:44px}h1{font:700 34px/1.2 system-ui;margin:0 0 10px}.muted{color:#9aabc7}
.status{display:flex;gap:18px;margin:28px 0}.card{background:#141c32;border:1px solid #2b3b61;border-radius:12px;padding:18px 22px;min-width:180px}
.value{font:700 30px system-ui;color:#70e1a1}.label{color:#9aabc7;margin-top:4px}table{width:100%;border-collapse:collapse;background:#11182a}
th,td{padding:12px 14px;border:1px solid #293750;text-align:left}th{background:#19243d;color:#bcd0f7}code{color:#ffd479}
.scope{margin-top:26px;padding:16px 18px;border-left:4px solid #f3b85b;background:#171a25}footer{margin-top:28px;color:#8291aa;font-size:13px}
</style></head><body><main>
<h1>P10 Node Supervisor — First Flow</h1>
<div class="muted">真实 Node 24.20.0 + 独立 Supervisor/guardian/harmless child；被测 core <code>${coreSha.slice(0, 8)}</code>，测试 <code>${testSha.slice(0, 8)}</code></div>
<div class="status"><div class="card"><div class="value">${summary.pass}/${summary.tests}</div><div class="label">tests passed</div></div>
<div class="card"><div class="value">${summary.fail}</div><div class="label">failures</div></div>
<div class="card"><div class="value">${(summary.duration_ms / 1000).toFixed(2)}s</div><div class="label">Node test duration</div></div></div>
<table><thead><tr><th>场景</th><th>Supervisor SIGKILL</th><th>actual starts</th><th>birth</th><th>exit</th><th>HTTP exchanges</th></tr></thead>
<tbody>${rows}</tbody></table>
<div class="scope">范围：四个 crash 窗口、同 operation 幂等、旧 runtime/control 身份、摘要冲突、结构化授权、inbox ownership 与真实退出。此图不代表 P09/P05/MAF/HostTransport/K8s 的完整 M2 集成。</div>
<footer>Command: WUJI_P10_EVIDENCE_DIR=docs/vnext/evidence/P10/node-first-flow/raw work/toolchain/bin/node --test … tests/task-workers/maf-supervisor.test.mjs</footer>
</main></body></html>`;
await writeFile(join(evidenceRoot, "result.html"), html);
await mkdir(join(evidenceRoot, "screenshots"), { recursive: true });

console.log(JSON.stringify({ evidenceRoot, summary, files: records.map(({ name }) => basename(name)) }));
