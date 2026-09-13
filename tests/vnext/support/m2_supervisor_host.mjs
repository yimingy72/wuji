import { readFileSync, writeFileSync } from "node:fs";

import { ControllerAdapter, mafProfile } from "../../../services/maf-supervisor/controller-adapter.mjs";
import { NodeSupervisor } from "../../../services/maf-supervisor/main.mjs";

const path = process.env.WUJI_M2_SUPERVISOR_CONFIG;
if (!path) throw new Error("WUJI_M2_SUPERVISOR_CONFIG is required");
const config = JSON.parse(readFileSync(path, "utf8"));
const adapter = new ControllerAdapter({
  origin: config.controllerOrigin,
  authorization: async () => config.receiverToken,
  receiver: config.receiver,
  timeoutMs: config.timeoutMs,
  maxResponseBytes: config.maxTransportBytes,
  maxRequestBytes: config.maxTransportBytes,
});
const supervisor = await NodeSupervisor.open({
  inboxDir: config.inboxDir,
  receiver: config.receiver,
  profiles: {
    [config.profileId]: mafProfile({
      pythonExecutable: config.pythonExecutable,
      cwd: config.cwd,
      env: config.env,
      workKinds: ["explore"],
    }),
  },
  authorize: adapter.authorize,
  bootstrap: adapter.bootstrap,
  persistResults: adapter.persistResults,
});
const server = supervisor.createServer({ authenticate: adapter.authenticate });

server.listen(0, "127.0.0.1", () => {
  const address = server.address();
  writeFileSync(
    config.readyFile,
    `${JSON.stringify({ host: address.address, port: address.port, pid: process.pid })}\n`,
    { mode: 0o600 },
  );
});

async function close() {
  await new Promise((resolve) => server.close(resolve));
  await supervisor.close();
}
for (const signal of ["SIGINT", "SIGTERM"]) {
  process.once(signal, () => close().finally(() => process.exit(0)));
}
