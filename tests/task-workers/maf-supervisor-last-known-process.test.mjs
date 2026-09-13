import assert from "node:assert/strict";
import { mkdir, mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import { NodeSupervisor } from "../../services/maf-supervisor/main.mjs";
import {
  digest,
  durableWrite,
  signed,
} from "../../services/maf-supervisor/protocol.mjs";
import { assignmentFor } from "./support/supervisor-harness.mjs";

test("unknown retains a verified running birth when guardian challenge fails", async () => {
  const directory = await mkdtemp(join(tmpdir(), "wuji-p10-last-known-"));
  const assignment = assignmentFor("last-known");
  const receiver = {
    receiver_id: assignment.identity.receiver_id,
    runtime_attempt: assignment.identity.runtime_attempt,
    environment_ref: "local-last-known",
    pod_uid: "pod-last-known",
  };
  const supervisor = await NodeSupervisor.open({
    inboxDir: join(directory, "inbox"),
    receiver,
    profiles: {},
    authorize: async ({ action, assignment_digest }) => ({
      identity: assignment.identity,
      assignment_digest,
      receiver,
      action,
      subject: "service:p10-controller",
      execution_allowed: true,
      valid_until: new Date(Date.now() + 60_000).toISOString(),
    }),
  });
  try {
    const launchId = "a".repeat(64);
    const secret = "b".repeat(64);
    const guardianBirth = "c".repeat(64);
    const launchDirectory = join(directory, "launch");
    const process = {
      pid: 4242,
      birth_id: `${launchId}:${guardianBirth}:verified-os-birth`,
      started_at: "2026-09-13T08:00:00.000Z",
      exited_at: null,
      exit_code: null,
    };
    const record = {
      operation_id: assignment.operation_id,
      assignment,
      assignment_digest: digest(assignment),
      receiver,
      profile_id: "harmless-node-v1",
      directory: launchDirectory,
      socket_path: join(directory, "missing-guardian.sock"),
      launch_id: launchId,
      secret,
      profile_digest: "d".repeat(64),
      state: "prepared",
      observation: null,
      prepared_at: "2026-09-13T07:59:59.000Z",
    };
    await mkdir(launchDirectory, { recursive: true, mode: 0o700 });
    durableWrite(
      join(launchDirectory, "process.json"),
      signed(
        {
          launch_id: launchId,
          identity: assignment.identity,
          receiver,
          assignment_digest: record.assignment_digest,
          guardian_birth_id: guardianBirth,
          guardian_pid: 4343,
          state: "running",
          process,
          reason: "verified running proof",
        },
        secret,
      ),
    );
    supervisor.inbox.insert(record);

    const observed = await supervisor.query(assignment.operation_id, {
      subject: "service:p10-controller",
    });

    assert.equal(observed.state, "unknown");
    assert.equal(observed.observation.kind, "unknown");
    assert.deepEqual(observed.observation.process, process);
    assert.deepEqual(
      JSON.parse(observed.observation.source_receipt).process,
      process,
    );
  } finally {
    await supervisor.close();
    await rm(directory, { recursive: true, force: true });
  }
});
