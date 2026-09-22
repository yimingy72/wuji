import assert from "node:assert/strict";
import { mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { parse } from "yaml";

import { NodeSupervisor } from "../../services/maf-supervisor/main.mjs";
import { ControllerAdapter } from "../../services/maf-supervisor/controller-adapter.mjs";
import { digest } from "../../services/maf-supervisor/protocol.mjs";
import {
  assignmentFor,
  waitFor,
} from "./support/supervisor-harness.mjs";

const supportDirectory = dirname(fileURLToPath(import.meta.url));
const child = join(supportDirectory, "support", "bridge-result-child.mjs");
const holdingChild = join(
  supportDirectory,
  "support",
  "bridge-result-hold-child.mjs",
);

test("controller receipt parsing preserves every schema rejection code", async () => {
  const schema = parse(await readFile(new URL("../../packages/contracts/openapi-v2.yaml", import.meta.url), "utf8"));
  const directory = await mkdtemp(join(tmpdir(), "wuji-controller-rejection-"));
  const assignment = assignmentFor("controller-rejection");
  const adapter = new ControllerAdapter({
    origin: "http://127.0.0.1:1", authorization: async () => "fixture",
    receiver: { receiver_id: assignment.identity.receiver_id,
      runtime_attempt: assignment.identity.runtime_attempt,
      environment_ref: "fixture", pod_uid: "fixture" },
  });
  const receipt = {
    submission_id: resultAck(assignment).submission_id,
    status: "rejected", components: [], request_id: "fixture", code: null,
  };
  adapter.post = async () => structuredClone(receipt);
  try {
    await writeFile(join(directory, "result-request.json"), JSON.stringify({ assignment }), { mode: 0o600 });
    for (const code of schema.components.schemas.ErrorCode.enum) {
      receipt.code = code;
      receipt.components = [{ status: "rejected", local_ref: "claim", request_id: "fixture", code }];
      const settlement = await adapter.persistResults({ assignment, directory });
      assert.deepEqual(settlement, { ...resultAck(assignment), receipt_digest: digest(receipt) }, code);
      assert.equal(receipt.status, "rejected");
    }
    for (const invalid of ["NOT_A_SCHEMA_CODE", 42, {}]) {
      receipt.code = invalid;
      receipt.components = [];
      await assert.rejects(adapter.persistResults({ assignment, directory }), { code: "INVALID_CONTROLLER_RESPONSE" });
      receipt.code = null;
      receipt.components = [{ status: "rejected", local_ref: "claim", request_id: "fixture", code: invalid }];
      await assert.rejects(adapter.persistResults({ assignment, directory }), { code: "INVALID_CONTROLLER_RESPONSE" });
    }
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

function resultAck(assignment) {
  return {
    schema_version: "wuji.worker-settlement.v1",
    kind: "result",
    assignment_digest: digest(assignment),
    submission_id: `maf-m1:${digest({
      identity: assignment.identity,
      operation_id: assignment.operation_id,
    })}`,
    receipt_digest: "a".repeat(64),
  };
}

async function fixture(label, persistResults, command = child) {
  const directory = await mkdtemp(join(tmpdir(), `wuji-m2-${label}-`));
  const assignment = assignmentFor(label);
  const receiver = {
    receiver_id: assignment.identity.receiver_id,
    runtime_attempt: assignment.identity.runtime_attempt,
    environment_ref: `local-${label}`,
    pod_uid: `pod-${label}`,
  };
  const supervisor = await NodeSupervisor.open({
    inboxDir: join(directory, "inbox"),
    receiver,
    profiles: {
      "harmless-node-v1": {
        command: process.execPath,
        args: [command],
        cwd: supportDirectory,
        env: {},
        workKinds: ["explore"],
      },
    },
    authorize: async ({ action, assignment_digest }) => ({
      identity: assignment.identity,
      assignment_digest,
      receiver,
      action,
      subject: "service:m2-controller",
      execution_allowed: true,
      valid_until: new Date(Date.now() + 60_000).toISOString(),
    }),
    persistResults,
  });
  return { assignment, directory, supervisor };
}

async function waitForExitedProof(directory) {
  await waitFor(async () => {
    const launches = await readdir(join(directory, "inbox", "launches"));
    if (launches.length !== 1) return null;
    const proof = JSON.parse(
      await readFile(
        join(directory, "inbox", "launches", launches[0], "process.json"),
        "utf8",
      ),
    );
    return proof.body.state === "exited";
  });
}

test("observe persists only actual files from the fixed worker directory", async () => {
  const calls = [];
  const settlements = [];
  const value = await fixture("persist-results", async ({ assignment, directory }) => {
    calls.push({
      assignment,
      directory,
      sdk: await readFile(join(directory, "sdk-request.json"), "utf8"),
      result: await readFile(join(directory, "result-request.json"), "utf8"),
    });
    const settlement = resultAck(assignment);
    settlements.push(settlement);
    return settlement;
  });
  try {
    await value.supervisor.start(
      {
        start_operation_id: value.assignment.operation_id,
        assignment: value.assignment,
        profile_id: "harmless-node-v1",
      },
      { subject: "service:m2-controller", directory: "/caller/untrusted" },
    );
    await waitForExitedProof(value.directory);
    const exited = await value.supervisor.query(
      value.assignment.operation_id,
      { subject: "service:m2-controller" },
    );

    assert.equal(exited.state, "exited", JSON.stringify(settlements));
    assert.equal(exited.observation.kind, "exited");
    assert.ok(calls.length >= 1);
    assert.deepEqual(calls.at(-1).assignment, value.assignment);
    assert.match(calls.at(-1).directory, /\/launches\/[a-f0-9]+\/worker$/);
    assert.notEqual(calls.at(-1).directory, "/caller/untrusted");
    assert.equal(JSON.parse(calls.at(-1).sdk).kind, "sdk");
    assert.equal(JSON.parse(calls.at(-1).result).kind, "result");
  } finally {
    await value.supervisor.close();
    await rm(value.directory, { recursive: true, force: true });
  }
});

test("a running child keeps ownership of its own result", async () => {
  const calls = [];
  const value = await fixture(
    "running-ownership",
    async ({ assignment }) => {
      calls.push(assignment.operation_id);
      return resultAck(assignment);
    },
    holdingChild,
  );
  try {
    await value.supervisor.start(
      {
        start_operation_id: value.assignment.operation_id,
        assignment: value.assignment,
        profile_id: "harmless-node-v1",
      },
      { subject: "service:m2-controller" },
    );
    const launches = await waitFor(async () => {
      const entries = await readdir(join(value.directory, "inbox", "launches"));
      return entries.length === 1 ? entries : null;
    });
    const worker = join(value.directory, "inbox", "launches", launches[0], "worker");
    await waitFor(async () => {
      const files = await readdir(worker);
      return files.includes("result-request.json");
    });

    const observed = await value.supervisor.query(
      value.assignment.operation_id,
      { subject: "service:m2-controller" },
    );

    // The child wrote the bytes it is about to submit and is still running, so
    // the supervisor must not recover them: committing here would make the
    // child's own submission another writer's replay.
    assert.equal(observed.state, "running");
    assert.deepEqual(calls, []);
  } finally {
    await value.supervisor.close();
    await rm(value.directory, { recursive: true, force: true });
  }
});

test("a result persistence failure cannot report the child as exited", async () => {
  let attempts = 0;
  const value = await fixture("persist-failure", async () => {
    attempts += 1;
    throw new Error("synthetic result sink failure");
  });
  try {
    await value.supervisor.start(
      {
        start_operation_id: value.assignment.operation_id,
        assignment: value.assignment,
        profile_id: "harmless-node-v1",
      },
      { subject: "service:m2-controller" },
    );
    const observed = await waitFor(async () => {
      const receipt = await value.supervisor.query(
        value.assignment.operation_id,
        { subject: "service:m2-controller" },
      );
      return attempts > 0 ? receipt : null;
    });

    assert.equal(observed.state, "unknown");
    assert.equal(observed.observation.kind, "unknown");
    assert.ok(attempts >= 1);
  } finally {
    await value.supervisor.close();
    await rm(value.directory, { recursive: true, force: true });
  }
});

for (const [label, persistResults] of [
  ["missing", undefined],
  ["empty", async () => null],
  [
    "invalid nested result",
    async () => ({
      submission_id: "submission-1",
      status: "accepted",
      components: [null],
      request_id: "request-1",
      code: "not-a-contract-error-code",
    }),
  ],
  [
    "result file with BlobRef",
    async () => ({ id: "sdk-artifact", version: "1", sha256: "a".repeat(64) }),
  ],
]) {
  test(`produced result files with a ${label} settlement stay unknown`, async () => {
    const value = await fixture(`persist-${label}`, persistResults);
    try {
      await value.supervisor.start(
        {
          start_operation_id: value.assignment.operation_id,
          assignment: value.assignment,
          profile_id: "harmless-node-v1",
        },
        { subject: "service:m2-controller" },
      );
      await waitForExitedProof(value.directory);
      const observed = await value.supervisor.query(
        value.assignment.operation_id,
        { subject: "service:m2-controller" },
      );

      assert.equal(observed.state, "unknown");
      assert.equal(observed.observation.kind, "unknown");
      assert.ok(observed.observation.process?.birth_id);
    } finally {
      await value.supervisor.close();
      await rm(value.directory, { recursive: true, force: true });
    }
  });
}
