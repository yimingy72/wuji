import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { setTimeout as delay } from "node:timers/promises";
import { fileURLToPath } from "node:url";

import { NodeSupervisor } from "../../services/maf-supervisor/main.mjs";
import {
  createSupervisorFixture,
  waitFor as waitForHarness,
} from "./support/supervisor-harness.mjs";

const harmlessChild = fileURLToPath(
  new URL("./support/harmless-child.mjs", import.meta.url),
);

const identity = {
  tenant_id: "tenant-p10",
  project_id: "project-p10",
  task_id: "task-p10",
  work_item_id: "work-p10",
  agent_run_id: "run-p10",
  execution_epoch: "1",
  run_epoch: "1",
  runtime_attempt: "1",
  receiver_id: "receiver-p10",
};

const assignment = {
  schema_version: "wuji.assignment.v2",
  operation_id: "start-p10-response-loss",
  identity,
  work_kind: "explore",
  snapshot_id: "snapshot-p10",
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

const receiver = {
  receiver_id: identity.receiver_id,
  runtime_attempt: identity.runtime_attempt,
  environment_ref: "local-p10-fixture",
  pod_uid: "pod-p10-fixture",
};

async function waitFor(check, timeoutMs = 5_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const result = await check();
    if (result) return result;
    await delay(10);
  }
  throw new Error(`condition was not met within ${timeoutMs}ms`);
}

async function countActualStarts(path) {
  try {
    const body = await readFile(path, "utf8");
    return body.split("\n").filter(Boolean).length;
  } catch (error) {
    if (error?.code === "ENOENT") return 0;
    throw error;
  }
}

async function expectCrash(fixture, host, window) {
  await waitForHarness(
    () => host.child.exitCode !== null || host.child.signalCode !== null,
  );
  assert.equal(host.child.signalCode, "SIGKILL");
  assert.deepEqual(await fixture.crashes(), [
    {
      window,
      operation_id: fixture.assignment.operation_id,
      pid: host.child.pid,
    },
  ]);
}

async function expectSingleProcessToExit(fixture, host) {
  const [actualStart] = await waitForHarness(async () => {
    const starts = await fixture.starts();
    return starts.length === 1 ? starts : null;
  });
  assert.equal(actualStart.operation_id, fixture.assignment.operation_id);
  assert.ok(Number.isSafeInteger(actualStart.pid) && actualStart.pid > 0);

  await fixture.release();
  const exited = await waitForHarness(async () => {
    const response = await fixture.request(host, "GET", fixture.startPath);
    return response.status === 200 && response.body.state === "exited"
      ? response.body
      : null;
  });
  assert.equal(exited.observation.kind, "exited");
  assert.equal(exited.observation.process.pid, actualStart.pid);
  assert.notEqual(exited.observation.process.birth_id, String(actualStart.pid));
  assert.ok(exited.observation.process.birth_id.includes(":"));
  assert.equal(exited.observation.process.exit_code, 0);
  assert.ok(exited.observation.process.exited_at);

  const events = await fixture.lifecycle();
  assert.deepEqual(
    events.map(({ event }) => event),
    ["birth", "exit"],
  );
  assert.equal(events[0].pid, actualStart.pid);
  assert.equal(events[1].pid, actualStart.pid);
  assert.equal(events[0].fixture_instance_id, actualStart.fixture_instance_id);
  assert.equal(events[1].fixture_instance_id, actualStart.fixture_instance_id);
}

test("redelivery after a lost running response reuses the actual process", async () => {
  const directory = await mkdtemp(join(tmpdir(), "wuji-p10-response-loss-"));
  const countFile = join(directory, "actual-starts.tsv");
  const lifecycleFile = join(directory, "child-lifecycle.jsonl");
  const releaseFile = join(directory, "release");
  let injectResponseLoss = true;

  const supervisor = await NodeSupervisor.open({
    inboxDir: join(directory, "inbox"),
    receiver,
    profiles: {
      "harmless-node-v1": {
        command: process.execPath,
        args: [harmlessChild],
        cwd: dirname(harmlessChild),
        env: {
          WUJI_P10_OPERATION_ID: assignment.operation_id,
          WUJI_P10_COUNT_FILE: countFile,
          WUJI_P10_LIFECYCLE_FILE: lifecycleFile,
          WUJI_P10_RELEASE_FILE: releaseFile,
          WUJI_P10_LIFETIME_MS: "30000",
        },
        workKinds: ["explore"],
      },
    },
    authorize: async ({
      action,
      assignment: authorizedAssignment,
      assignment_digest,
      receiver: authorizedReceiver,
    }) => ({
      identity: authorizedAssignment.identity,
      assignment_digest,
      receiver: authorizedReceiver,
      action,
      subject: "service:p10-test-controller",
      execution_allowed: true,
      valid_until: new Date(Date.now() + 60_000).toISOString(),
    }),
    fault: async (window) => {
      if (window === "after_running_before_response" && injectResponseLoss) {
        injectResponseLoss = false;
        throw new Error("injected response loss");
      }
    },
  });

  try {
    await assert.rejects(
      supervisor.start(
        {
          start_operation_id: assignment.operation_id,
          assignment,
          profile_id: "harmless-node-v1",
        },
        "test-controller-token",
      ),
      /injected response loss/,
    );
    await waitFor(async () => (await countActualStarts(countFile)) === 1);

    const replay = await supervisor.start(
      {
        start_operation_id: assignment.operation_id,
        assignment,
        profile_id: "harmless-node-v1",
      },
      "test-controller-token",
    );

    assert.equal(replay.operation_id, assignment.operation_id);
    assert.equal(replay.state, "running");
    assert.equal(await countActualStarts(countFile), 1);
  } finally {
    await writeFile(releaseFile, "release\n", { mode: 0o600 });
    await waitFor(async () => {
      try {
        return (await supervisor.query(
          assignment.operation_id,
          "test-controller-token",
        )).state === "exited";
      } catch {
        return false;
      }
    });
    await supervisor.close();
    await rm(directory, { recursive: true, force: true });
  }
});

test("a crash after prepared and before spawn becomes unknown without spawning", async () => {
  const fixture = await createSupervisorFixture("prepared-before-spawn");
  try {
    const crashingHost = await fixture.launch("after_prepared_before_spawn");
    await assert.rejects(
      fixture.request(
        crashingHost,
        "PUT",
        fixture.startPath,
        fixture.startBody,
      ),
    );
    await expectCrash(fixture, crashingHost, "after_prepared_before_spawn");

    const restartedHost = await fixture.launch();
    const query = await fixture.request(
      restartedHost,
      "GET",
      fixture.startPath,
    );
    assert.equal(query.status, 200);
    assert.equal(query.body.state, "unknown");
    assert.deepEqual(await fixture.starts(), []);

    const replay = await fixture.request(
      restartedHost,
      "PUT",
      fixture.startPath,
      fixture.startBody,
    );
    assert.equal(replay.status, 200);
    assert.equal(replay.body.state, "unknown");
    assert.deepEqual(await fixture.starts(), []);
  } finally {
    await fixture.cleanup();
  }
});

test("a crash before prepared leaves no operation and redelivery spawns once", async () => {
  const fixture = await createSupervisorFixture("before-prepared");
  try {
    const crashingHost = await fixture.launch("before_prepared");
    await assert.rejects(
      fixture.request(
        crashingHost,
        "PUT",
        fixture.startPath,
        fixture.startBody,
      ),
    );
    await expectCrash(fixture, crashingHost, "before_prepared");
    assert.deepEqual(await fixture.starts(), []);

    const restartedHost = await fixture.launch();
    const absent = await fixture.request(
      restartedHost,
      "GET",
      fixture.startPath,
    );
    assert.equal(absent.status, 404);
    assert.equal(absent.body.code, "OPERATION_NOT_FOUND");

    const started = await fixture.request(
      restartedHost,
      "PUT",
      fixture.startPath,
      fixture.startBody,
    );
    assert.equal(started.status, 200);
    assert.equal(started.body.state, "running");
    await expectSingleProcessToExit(fixture, restartedHost);
    assert.equal((await fixture.starts()).length, 1);
  } finally {
    await fixture.cleanup();
  }
});

for (const [window, label] of [
  [
    "after_spawn_before_running_receipt",
    "after actual spawn and before the running receipt",
  ],
  [
    "after_running_before_response",
    "after the running receipt and before the response",
  ],
]) {
  test(`a crash ${label} never spawns the operation twice`, async () => {
    const fixture = await createSupervisorFixture(window.replaceAll("_", "-"));
    try {
      const crashingHost = await fixture.launch(window);
      await assert.rejects(
        fixture.request(
          crashingHost,
          "PUT",
          fixture.startPath,
          fixture.startBody,
        ),
      );
      await expectCrash(fixture, crashingHost, window);
      await waitForHarness(async () => (await fixture.starts()).length === 1);

      const restartedHost = await fixture.launch();
      const query = await fixture.request(
        restartedHost,
        "GET",
        fixture.startPath,
      );
      assert.equal(query.status, 200);
      assert.equal(query.body.state, "running");

      const replay = await fixture.request(
        restartedHost,
        "PUT",
        fixture.startPath,
        fixture.startBody,
      );
      assert.equal(replay.status, 200);
      assert.equal(replay.body.state, "running");
      assert.equal((await fixture.starts()).length, 1);

      await expectSingleProcessToExit(fixture, restartedHost);
      assert.equal((await fixture.starts()).length, 1);
    } finally {
      await fixture.cleanup();
    }
  });
}

test("an assignment from an old runtime attempt is rejected before spawn", async () => {
  const fixture = await createSupervisorFixture("old-runtime", {
    runtimeAttempt: "2",
  });
  try {
    const host = await fixture.launch();
    const oldBody = structuredClone(fixture.startBody);
    oldBody.assignment.identity.runtime_attempt = "1";

    const rejected = await fixture.request(
      host,
      "PUT",
      fixture.startPath,
      oldBody,
    );
    assert.equal(rejected.status, 409);
    assert.equal(rejected.body.code, "STALE_EXECUTION");
    assert.deepEqual(await fixture.starts(), []);

    const current = await fixture.request(
      host,
      "PUT",
      fixture.startPath,
      fixture.startBody,
    );
    assert.equal(current.status, 200);
    assert.equal(current.body.state, "running");
    await expectSingleProcessToExit(fixture, host);
  } finally {
    await fixture.cleanup();
  }
});

test("redelivery with a different assignment digest is rejected without another spawn", async () => {
  const fixture = await createSupervisorFixture("digest-conflict");
  try {
    const host = await fixture.launch();
    const started = await fixture.request(
      host,
      "PUT",
      fixture.startPath,
      fixture.startBody,
    );
    assert.equal(started.status, 200);
    assert.equal(started.body.state, "running");
    await waitForHarness(async () => (await fixture.starts()).length === 1);

    const conflictingBody = structuredClone(fixture.startBody);
    conflictingBody.assignment.snapshot_id = "snapshot-conflicting";
    const conflict = await fixture.request(
      host,
      "PUT",
      fixture.startPath,
      conflictingBody,
    );
    assert.equal(conflict.status, 409);
    assert.equal(conflict.body.code, "INPUT_DIGEST_CONFLICT");
    assert.equal((await fixture.starts()).length, 1);

    await expectSingleProcessToExit(fixture, host);
    assert.equal((await fixture.starts()).length, 1);
  } finally {
    await fixture.cleanup();
  }
});

test("stop rejects stale identity and accepted control waits for actual exit", async () => {
  const fixture = await createSupervisorFixture("control-exit", {
    sigtermDelayMs: 750,
  });
  try {
    const host = await fixture.launch();
    const started = await fixture.request(
      host,
      "PUT",
      fixture.startPath,
      fixture.startBody,
    );
    assert.equal(started.status, 200);
    assert.equal(started.body.state, "running");
    await waitForHarness(async () => (await fixture.starts()).length === 1);

    const staleIdentity = structuredClone(fixture.assignment.identity);
    staleIdentity.run_epoch = "0";
    const staleControl = await fixture.request(
      host,
      "POST",
      `${fixture.startPath}/control`,
      {
        control_operation_id: "stop-stale",
        action: "stop",
        identity: staleIdentity,
      },
    );
    assert.equal(staleControl.status, 409);
    assert.equal(staleControl.body.code, "STALE_EXECUTION");

    const controlBody = {
      control_operation_id: "stop-current",
      action: "stop",
      identity: fixture.assignment.identity,
    };
    const accepted = await fixture.request(
      host,
      "POST",
      `${fixture.startPath}/control`,
      controlBody,
    );
    assert.equal(accepted.status, 200);
    assert.equal(accepted.body.status, "accepted");
    assert.equal(accepted.body.execution.state, "running");

    const replay = await fixture.request(
      host,
      "POST",
      `${fixture.startPath}/control`,
      controlBody,
    );
    assert.equal(replay.status, 200);
    assert.equal(replay.body.status, "accepted");
    assert.equal(replay.body.accepted_at, accepted.body.accepted_at);
    assert.equal((await fixture.starts()).length, 1);

    await delay(700);
    const exited = await waitForHarness(async () => {
      const response = await fixture.request(host, "GET", fixture.startPath);
      return response.status === 200 && response.body.state === "exited"
        ? response.body
        : null;
    });
    assert.equal(exited.observation.kind, "exited");
    assert.equal(exited.observation.process.exit_code, 0);
    assert.ok(exited.observation.process.exited_at);
    assert.equal((await fixture.starts()).length, 1);
    assert.deepEqual(
      (await fixture.lifecycle()).map(({ event, reason }) => ({ event, reason })),
      [
        { event: "birth", reason: undefined },
        { event: "exit", reason: "SIGTERM" },
      ],
    );
  } finally {
    await fixture.cleanup();
  }
});

test("a bare boolean permission cannot start a process", async () => {
  const directory = await mkdtemp(join(tmpdir(), "wuji-p10-boolean-grant-"));
  const countFile = join(directory, "actual-starts.tsv");
  const lifecycleFile = join(directory, "child-lifecycle.jsonl");
  const releaseFile = join(directory, "release");
  const supervisor = await NodeSupervisor.open({
    inboxDir: join(directory, "inbox"),
    receiver,
    profiles: {
      "harmless-node-v1": {
        command: process.execPath,
        args: [harmlessChild],
        cwd: dirname(harmlessChild),
        env: {
          WUJI_P10_OPERATION_ID: assignment.operation_id,
          WUJI_P10_COUNT_FILE: countFile,
          WUJI_P10_LIFECYCLE_FILE: lifecycleFile,
          WUJI_P10_RELEASE_FILE: releaseFile,
        },
        workKinds: ["explore"],
      },
    },
    authorize: async () => true,
  });
  try {
    await assert.rejects(
      supervisor.start(
        {
          start_operation_id: assignment.operation_id,
          assignment,
          profile_id: "harmless-node-v1",
        },
        "test-controller-token",
      ),
      (error) => error?.code === "STALE_EXECUTION" && error?.status === 403,
    );
    assert.equal(await countActualStarts(countFile), 0);
  } finally {
    await supervisor.close();
    await rm(directory, { recursive: true, force: true });
  }
});

test("one inbox has one owner and keeps its receiver identity across reopen", async () => {
  const directory = await mkdtemp(join(tmpdir(), "wuji-p10-inbox-owner-"));
  const options = {
    inboxDir: join(directory, "inbox"),
    receiver,
    profiles: {},
    authorize: async () => {
      throw new Error("authorization is not used in this ownership test");
    },
  };
  const first = await NodeSupervisor.open(options);
  try {
    await assert.rejects(
      NodeSupervisor.open(options),
      (error) => error?.code === "INBOX_UNAVAILABLE_OR_OWNED",
    );
  } finally {
    await first.close();
  }

  const reopened = await NodeSupervisor.open(options);
  await reopened.close();
  await assert.rejects(
    NodeSupervisor.open({
      ...options,
      receiver: { ...receiver, runtime_attempt: "2" },
    }),
    (error) => error?.code === "RECEIVER_IDENTITY_CONFLICT",
  );
  await rm(directory, { recursive: true, force: true });
});
