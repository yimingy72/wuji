import { writeFile } from "node:fs/promises";
import { join } from "node:path";

const directory = process.env.WUJI_WORKER_BOOTSTRAP_DIRECTORY;
if (!directory) throw new Error("WUJI_WORKER_BOOTSTRAP_DIRECTORY is required");

// A live child owns its own submission: it writes the exact bytes it is about to
// post and keeps running until its Host call is answered.
await writeFile(
  join(directory, "result-request.json"),
  `${JSON.stringify({ kind: "result", bytes: "cmF3" })}\n`,
  { mode: 0o600 },
);
await new Promise((resolve) => setTimeout(resolve, 120_000));
