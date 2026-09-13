import { randomUUID } from "node:crypto";
import { appendFileSync, existsSync } from "node:fs";

const requiredEnvironment = [
  "WUJI_P10_OPERATION_ID",
  "WUJI_P10_COUNT_FILE",
  "WUJI_P10_LIFECYCLE_FILE",
];

for (const name of requiredEnvironment) {
  if (!process.env[name]) {
    throw new Error(`missing required fixture environment: ${name}`);
  }
}

const operationId = process.env.WUJI_P10_OPERATION_ID;
const fixtureInstanceId = randomUUID();
const countFile = process.env.WUJI_P10_COUNT_FILE;
const lifecycleFile = process.env.WUJI_P10_LIFECYCLE_FILE;
const releaseFile = process.env.WUJI_P10_RELEASE_FILE;
const configuredLifetime = Number.parseInt(
  process.env.WUJI_P10_LIFETIME_MS ?? "30000",
  10,
);
const lifetimeMs = Number.isSafeInteger(configuredLifetime)
  ? Math.min(Math.max(configuredLifetime, 1), 120_000)
  : 30_000;
const configuredSigtermDelay = Number.parseInt(
  process.env.WUJI_P10_SIGTERM_DELAY_MS ?? "0",
  10,
);
const sigtermDelayMs = Number.isSafeInteger(configuredSigtermDelay)
  ? Math.min(Math.max(configuredSigtermDelay, 0), 5_000)
  : 0;

function appendLifecycle(event, detail = {}) {
  appendFileSync(
    lifecycleFile,
    `${JSON.stringify({
      event,
      operation_id: operationId,
      fixture_instance_id: fixtureInstanceId,
      pid: process.pid,
      ppid: process.ppid,
      observed_at: new Date().toISOString(),
      monotonic_ns: process.hrtime.bigint().toString(),
      ...detail,
    })}\n`,
    { encoding: "utf8", mode: 0o600 },
  );
}

let finished = false;
function finish(reason, code = 0) {
  if (finished) return;
  finished = true;
  appendLifecycle("exit", { reason, exit_code: code });
  process.exit(code);
}

process.once("SIGTERM", () => {
  if (sigtermDelayMs === 0) finish("SIGTERM");
  else setTimeout(() => finish("SIGTERM"), sigtermDelayMs);
});
process.once("SIGINT", () => finish("SIGINT"));

// The count line doubles as the fixture-ready marker: control tests wait for
// it, so a signal cannot race ahead of these handlers and fake a raw OS kill.
appendFileSync(countFile, `${operationId}\t${fixtureInstanceId}\t${process.pid}\n`, {
  encoding: "utf8",
  mode: 0o600,
});
appendLifecycle("birth");

const deadline = Date.now() + lifetimeMs;
const timer = setInterval(() => {
  if (releaseFile && existsSync(releaseFile)) {
    clearInterval(timer);
    finish("release_file");
  } else if (Date.now() >= deadline) {
    clearInterval(timer);
    finish("fixture_timeout");
  }
}, 10);
timer.unref();

await new Promise((resolve) => {
  process.once("exit", resolve);
  setTimeout(resolve, lifetimeMs + 1_000);
});
