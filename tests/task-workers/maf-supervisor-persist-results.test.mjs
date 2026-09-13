import assert from "node:assert/strict";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { NodeSupervisor } from "../../services/maf-supervisor/main.mjs";
import {
  assignmentFor,
  waitFor,
} from "./support/supervisor-harness.mjs";

const supportDirectory = dirname(fileURLToPath(import.meta.url));
const child = join(supportDirectory, "support", "bridge-result-child.mjs");

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

test("observe persists only actual files from the fixed worker directory", async () => {
  const calls = [];
  const value = await fixture("persist-results", async ({ assignment, directory }) => {
    calls.push({
      assignment,
      directory,
      sdk: await readFile(join(directory, "sdk-request.json"), "utf8"),
      result: await readFile(join(directory, "result-request.json"), "utf8"),
    });
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
    const exited = await waitFor(async () => {
      const receipt = await value.supervisor.query(
        value.assignment.operation_id,
        { subject: "service:m2-controller" },
      );
      return receipt.state === "exited" ? receipt : null;
    });

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
