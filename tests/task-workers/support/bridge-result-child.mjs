import { writeFile } from "node:fs/promises";
import { join } from "node:path";

const directory = process.env.WUJI_WORKER_BOOTSTRAP_DIRECTORY;
if (!directory) throw new Error("WUJI_WORKER_BOOTSTRAP_DIRECTORY is required");

await writeFile(
  join(directory, "sdk-request.json"),
  `${JSON.stringify({ kind: "sdk", bytes: "c2Rr" })}\n`,
  { mode: 0o600 },
);
await writeFile(
  join(directory, "result-request.json"),
  `${JSON.stringify({ kind: "result", bytes: "cmF3" })}\n`,
  { mode: 0o600 },
);
