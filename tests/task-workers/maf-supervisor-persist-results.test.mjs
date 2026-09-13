import assert from "node:assert/strict";
import { mkdtemp, readFile, readdir, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { NodeSupervisor } from "../../services/maf-supervisor/main.mjs";
import { digest } from "../../services/maf-supervisor/protocol.mjs";
import {
  assignmentFor,
  waitFor,
} from "./support/supervisor-harness.mjs";

const supportDirectory = dirname(fileURLToPath(import.meta.url));
const child = join(supportDirectory, "support", "bridge-result-child.mjs");

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

async function fixture(label, persistResults) {
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
        args: [child],
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
