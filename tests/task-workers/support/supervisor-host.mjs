import { appendFileSync, readFileSync, writeFileSync } from "node:fs";

import { NodeSupervisor } from "../../../services/maf-supervisor/main.mjs";

const configPath = process.env.WUJI_P10_SUPERVISOR_CONFIG;
if (!configPath) {
  throw new Error("WUJI_P10_SUPERVISOR_CONFIG is required");
}

const config = JSON.parse(readFileSync(configPath, "utf8"));
const supervisor = await NodeSupervisor.open({
  inboxDir: config.inboxDir,
  receiver: config.receiver,
  profiles: config.profiles,
  authorize: async ({
    action,
    assignment,
    assignment_digest,
    receiver,
    auth,
  }) => {
    if (auth?.subject !== config.controllerSubject) {
      throw new Error("controller subject rejected");
    }
    return {
      identity: assignment.identity,
      assignment_digest,
      receiver,
      action,
      subject: auth.subject,
      execution_allowed: true,
      valid_until: new Date(Date.now() + 60_000).toISOString(),
    };
  },
  fault: async (window, { operation_id }) => {
    if (window !== config.faultWindow) return;
    appendFileSync(
      config.crashMarkerFile,
      `${JSON.stringify({ window, operation_id, pid: process.pid })}\n`,
      { encoding: "utf8", mode: 0o600 },
    );
    process.kill(process.pid, "SIGKILL");
    await new Promise(() => {});
  },
});

const server = supervisor.createServer({
  authenticate: async (request) => {
    if (request.headers.authorization !== `Bearer ${config.controllerToken}`) {
      throw new Error("controller authentication rejected");
    }
    return { subject: config.controllerSubject };
  },
});

server.listen(0, "127.0.0.1", () => {
  const address = server.address();
  writeFileSync(
    config.readyFile,
    `${JSON.stringify({ host: address.address, port: address.port, pid: process.pid })}\n`,
    { encoding: "utf8", mode: 0o600 },
  );
});

async function shutdown() {
  await new Promise((resolve) => server.close(resolve));
  await supervisor.close();
}

process.once("SIGTERM", () => {
  shutdown().finally(() => process.exit(0));
});
process.once("SIGINT", () => {
  shutdown().finally(() => process.exit(0));
});
