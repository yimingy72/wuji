import { spawn } from "node:child_process";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { setTimeout as delay } from "node:timers/promises";
import { fileURLToPath } from "node:url";

const supportDirectory = dirname(fileURLToPath(import.meta.url));
const harmlessChild = join(supportDirectory, "harmless-child.mjs");
const supervisorHost = join(supportDirectory, "supervisor-host.mjs");

export const controllerToken = "p10-test-controller-token";

export function assignmentFor(label, overrides = {}) {
  const runtimeAttempt = overrides.runtimeAttempt ?? "1";
  const operationId = `start-${label}`;
  return {
    schema_version: "wuji.assignment.v2",
    operation_id: operationId,
    identity: {
      tenant_id: "tenant-p10",
      project_id: "project-p10",
      task_id: `task-${label}`,
      work_item_id: `work-${label}`,
      agent_run_id: `run-${label}`,
      execution_epoch: overrides.executionEpoch ?? "1",
      run_epoch: overrides.runEpoch ?? "1",
      runtime_attempt: runtimeAttempt,
      receiver_id: overrides.receiverId ?? "receiver-p10",
    },
    work_kind: "explore",
    snapshot_id: `snapshot-${label}`,
    profile_refs: ["harmless-node-v1"],
    session_manifest_ref: null,
    tool_definition_refs: ["read_record:v1"],
    limits: {
      max_work_items: 4,
      max_reason_runs: 1,
      max_model_requests: 2,
      max_tool_calls: 2,
      max_single_output_bytes: 65_536,
      max_total_output_bytes: 131_072,
      max_elapsed_seconds: 30,
      max_attempts_per_work: 1,
      repair_attempts: 0,
    },
    resume_reason: null,
  };
}

export async function waitFor(check, timeoutMs = 5_000) {
  const deadline = Date.now() + timeoutMs;
  let lastError;
  while (Date.now() < deadline) {
    try {
      const result = await check();
      if (result) return result;
    } catch (error) {
      lastError = error;
    }
    await delay(10);
  }
  throw new Error(
    `condition was not met within ${timeoutMs}ms${lastError ? `: ${lastError.message}` : ""}`,
  );
}

async function readText(path) {
  try {
    return await readFile(path, "utf8");
  } catch (error) {
    if (error?.code === "ENOENT") return "";
    throw error;
  }
}

export async function createSupervisorFixture(label, options = {}) {
  const directory = await mkdtemp(join(tmpdir(), `wuji-p10-${label}-`));
  const assignment = assignmentFor(label, {
    runtimeAttempt: options.runtimeAttempt,
  });
  const paths = {
    config: join(directory, "supervisor-config.json"),
    ready: join(directory, "supervisor-ready.json"),
    crashes: join(directory, "supervisor-crashes.jsonl"),
    count: join(directory, "actual-starts.tsv"),
    lifecycle: join(directory, "child-lifecycle.jsonl"),
    release: join(directory, "release"),
  };
  const receiver = {
    receiver_id: assignment.identity.receiver_id,
    runtime_attempt: assignment.identity.runtime_attempt,
    environment_ref: `local-${label}`,
    pod_uid: `pod-${label}`,
  };
  const baseConfig = {
    inboxDir: join(directory, "inbox"),
    receiver,
    controllerSubject: "service:p10-test-controller",
    controllerToken,
    readyFile: paths.ready,
    crashMarkerFile: paths.crashes,
    profiles: {
      "harmless-node-v1": {
        command: process.execPath,
        args: [harmlessChild],
        cwd: supportDirectory,
        env: {
          WUJI_P10_OPERATION_ID: assignment.operation_id,
          WUJI_P10_COUNT_FILE: paths.count,
          WUJI_P10_LIFECYCLE_FILE: paths.lifecycle,
          WUJI_P10_RELEASE_FILE: paths.release,
          WUJI_P10_LIFETIME_MS: String(options.lifetimeMs ?? 10_000),
          WUJI_P10_SIGTERM_DELAY_MS: String(options.sigtermDelayMs ?? 0),
        },
        workKinds: ["explore"],
      },
    },
  };
  let activeHost = null;
  const httpExchanges = [];

  async function launch(faultWindow = null) {
    if (
      activeHost &&
      activeHost.exitCode === null &&
      activeHost.signalCode === null
    ) {
      throw new Error("supervisor host is already running");
    }
    await rm(paths.ready, { force: true });
    await writeFile(
      paths.config,
      `${JSON.stringify({ ...baseConfig, faultWindow })}\n`,
      { mode: 0o600 },
    );
    const child = spawn(process.execPath, [supervisorHost], {
      cwd: supportDirectory,
      env: { WUJI_P10_SUPERVISOR_CONFIG: paths.config },
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString("utf8");
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString("utf8");
    });
    activeHost = child;
    const ready = await waitFor(async () => {
      const body = await readText(paths.ready);
      if (body) return JSON.parse(body);
      if (child.exitCode !== null || child.signalCode !== null) {
        throw new Error(
          `supervisor host exited ${child.exitCode}: ${stderr || stdout}`,
        );
      }
      return null;
    });
    return { child, ready, stdout: () => stdout, stderr: () => stderr };
  }

  async function request(host, method, path, body) {
    const headers = { Authorization: `Bearer ${controllerToken}` };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const url = `http://${host.ready.host}:${host.ready.port}${path}`;
    const requestRecord = {
      method,
      url,
      headers,
      body: body === undefined ? null : body,
    };
    try {
      const response = await fetch(url, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      const responseText = await response.text();
      const result = {
        status: response.status,
        headers: Object.fromEntries(response.headers),
        body: responseText ? JSON.parse(responseText) : null,
        responseText,
      };
      httpExchanges.push({ request: requestRecord, response: result });
      return result;
    } catch (error) {
      httpExchanges.push({
        request: requestRecord,
        response: null,
        error: { name: error.name, message: error.message },
      });
      throw error;
    }
  }

  async function starts() {
    const body = await readText(paths.count);
    return body
      .split("\n")
      .filter(Boolean)
      .map((line) => {
        const [operation_id, fixture_instance_id, pid] = line.split("\t");
        return { operation_id, fixture_instance_id, pid: Number(pid) };
      });
  }

  async function lifecycle() {
    const body = await readText(paths.lifecycle);
    return body.split("\n").filter(Boolean).map((line) => JSON.parse(line));
  }

  async function crashes() {
    const body = await readText(paths.crashes);
    return body.split("\n").filter(Boolean).map((line) => JSON.parse(line));
  }

  async function release() {
    await writeFile(paths.release, "release\n", { mode: 0o600 });
  }

  async function stopHost() {
    if (
      !activeHost ||
      activeHost.exitCode !== null ||
      activeHost.signalCode !== null
    ) return;
    const exited = new Promise((resolve) => activeHost.once("exit", resolve));
    activeHost.kill("SIGTERM");
    const timedOut = await Promise.race([
      exited.then(() => false),
      delay(2_000).then(() => true),
    ]);
    if (timedOut) {
      activeHost.kill("SIGKILL");
      await exited;
    }
  }

  async function persistEvidence() {
    const evidenceDirectory = process.env.WUJI_P10_EVIDENCE_DIR;
    if (!evidenceDirectory) return;
    await mkdir(evidenceDirectory, { recursive: true, mode: 0o700 });
    await writeFile(
      join(evidenceDirectory, `${label}.json`),
      `${JSON.stringify(
        {
          schema_version: "wuji.p10-node-fixture.v1",
          generated_at: new Date().toISOString(),
          label,
          assignment,
          receiver,
          actual_starts: await starts(),
          child_lifecycle: await lifecycle(),
          supervisor_crashes: await crashes(),
          http_exchanges: httpExchanges,
        },
        null,
        2,
      )}\n`,
      { mode: 0o600 },
    );
  }

  async function cleanup() {
    await persistEvidence();
    await release();
    await stopHost();
    await delay(50);
    await rm(directory, { recursive: true, force: true });
  }

  return {
    assignment,
    receiver,
    paths,
    launch,
    request,
    starts,
    lifecycle,
    crashes,
    release,
    httpExchanges: () => structuredClone(httpExchanges),
    stopHost,
    cleanup,
    startPath: `/operations/${encodeURIComponent(assignment.operation_id)}`,
    startBody: { assignment, profile_id: "harmless-node-v1" },
  };
}
