// Trusted per-launch process witness. It outlives the HTTP receiver, not the
// execution environment. The Worker is never given the signing key or socket.
import { spawn } from 'node:child_process';
import { createServer } from 'node:net';
import { closeSync, fsyncSync, openSync, readFileSync, writeSync } from 'node:fs';
import { constants } from 'node:os';
import { join } from 'node:path';
import { canonical, durableWrite, nonce, now, parseJson, signed, verified } from './protocol.mjs';

const directory = process.argv[2];
const manifest = parseJson(readFileSync(join(directory, 'launch.json'), 'utf8'));
const { launch_id, secret, command, args, env, cwd, identity, receiver, assignment_digest } = manifest;
const proofPath = join(directory, 'process.json');
const guardianBirth = nonce();
let worker, processRecord = null, state = 'prepared', failure = null, closed = false;
const controls = new Map();

function proof() {
  return { launch_id, identity, receiver, assignment_digest, guardian_birth_id: guardianBirth,
    guardian_pid: process.pid, state, process: processRecord, reason: failure ?? state };
}
function persist() { durableWrite(proofPath, signed(proof(), secret)); }
function osBirth(pid) {
  // Linux start ticks and boot ID supplement the live ChildProcess witness.
  // Other OSes still use the unique guardian/launch witness, never PID probing.
  try {
    const stat = readFileSync(`/proc/${pid}/stat`, 'utf8');
    return `${readFileSync('/proc/sys/kernel/random/boot_id', 'utf8').trim()}:${stat.slice(stat.lastIndexOf(')') + 2).split(' ')[19]}`;
  } catch { return 'child-process-spawn-event'; }
}
const logs = ['stdout', 'stderr'].map(name => ({ fd: openSync(join(directory, `${name}.log`), 'wx', 0o600), retained: 0 }));
function drain(stream, log) {
  stream.on('data', bytes => {
    // Drain all pipe bytes so a full log cannot deadlock the actual worker.
    const size = Math.min(bytes.length, Math.max(0, manifest.max_log_bytes - log.retained));
    if (size) { writeSync(log.fd, bytes.subarray(0, size)); log.retained += size; }
  });
}
function finish() {
  if (closed) return; closed = true;
  for (const log of logs) { fsyncSync(log.fd); closeSync(log.fd); }
  server.close();
}

const server = createServer(socket => {
  let input = ''; socket.setTimeout(1500, () => socket.destroy());
  socket.on('error', () => {});
  socket.on('data', bytes => {
    input += bytes.toString('utf8');
    if (Buffer.byteLength(input) > 65536) return socket.destroy();
    if (!input.includes('\n')) return;
    try {
      const request = verified(parseJson(input.slice(0, input.indexOf('\n'))), secret);
      if (request.launch_id !== launch_id || typeof request.challenge !== 'string') return socket.destroy();
      if (request.action === 'stop' && typeof request.control_id === 'string') {
        if (!controls.has(request.control_id)) {
          // Intent before signal. A replay cannot mean another Worker spawn.
          controls.set(request.control_id, now());
          durableWrite(join(directory, 'controls.json'), signed({ launch_id, controls: [...controls] }, secret));
          if (worker && state === 'running') worker.kill('SIGTERM');
        }
      } else if (request.action !== 'query') return socket.destroy();
      socket.end(canonical(signed({ launch_id, challenge: request.challenge, proof: proof() }, secret)) + '\n');
    } catch { socket.destroy(); }
  });
});
server.on('error', () => { process.exitCode = 1; });
server.listen(manifest.socket_path, () => {
  persist(); // trusted guardian is alive; not evidence the Worker was born
  try {
    worker = spawn(command, args, { cwd, env, shell: false, stdio: ['ignore', 'pipe', 'pipe'] });
    drain(worker.stdout, logs[0]); drain(worker.stderr, logs[1]);
    worker.once('spawn', () => {
      processRecord = { pid: worker.pid,
        birth_id: `${launch_id}:${guardianBirth}:${osBirth(worker.pid)}`,
        started_at: now(), exited_at: null, exit_code: null };
      state = 'running'; persist();
    });
    worker.once('error', error => {
      if (!processRecord) { state = 'not_started'; failure = `os_spawn_failed:${error.code ?? 'UNKNOWN'}`; persist(); }
    });
    worker.once('exit', (code, signal) => {
      if (!processRecord) return; // no fabricated birth if no OS spawn event
      processRecord = { ...processRecord, exited_at: now(),
        exit_code: code ?? 128 + (constants.signals[signal] ?? 0) };
      state = 'exited'; persist();
    });
    worker.once('close', finish);
  } catch (error) {
    state = 'not_started'; failure = `os_spawn_failed:${error.code ?? 'UNKNOWN'}`; persist(); finish();
  }
});
