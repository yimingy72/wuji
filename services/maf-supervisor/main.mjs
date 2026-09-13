import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { createServer as createTlsServer } from 'node:https';
import { existsSync, mkdirSync, mkdtempSync } from 'node:fs';
import { isAbsolute, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { setTimeout as delay } from 'node:timers/promises';
import { DurableInbox } from './inbox.mjs';
import { canonical, digest, durableWrite, equal, guardianRequest, nonce, now, parseJson,
  readProof, SupervisorError } from './protocol.mjs';

export { SupervisorError } from './protocol.mjs';
const identityKeys = ['tenant_id', 'project_id', 'task_id', 'work_item_id', 'agent_run_id',
  'execution_epoch', 'run_epoch', 'runtime_attempt', 'receiver_id'];
const receiverKeys = ['receiver_id', 'runtime_attempt', 'environment_ref', 'pod_uid'];
const revision = /^(0|[1-9][0-9]*)$/;
const text = (v, max = 256) => typeof v === 'string' && v.length > 0 && v.length <= max;
function exactKeys(value, keys) {
  return value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
}
function validateIdentity(identity) {
  if (!exactKeys(identity, identityKeys) || identityKeys.some(k => !text(identity[k]))
      || ['execution_epoch', 'run_epoch', 'runtime_attempt'].some(k => !revision.test(identity[k]))) {
    throw new SupervisorError('INVALID_RUN_IDENTITY', 422);
  }
}
function durableSettlement(value, record, kind) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  if (kind === 'result' && exactKeys(value, [
    'schema_version', 'kind', 'assignment_digest', 'submission_id', 'receipt_digest',
  ])) {
    return value.schema_version === 'wuji.worker-settlement.v1'
      && value.kind === kind && value.assignment_digest === record.assignment_digest
      && value.submission_id === `maf-m1:${digest({
        identity: record.assignment.identity,
        operation_id: record.assignment.operation_id,
      })}`
      && typeof value.receipt_digest === 'string'
      && /^[a-f0-9]{64}$/.test(value.receipt_digest);
  }
  if (kind === 'archive' && exactKeys(value, [
    'schema_version', 'kind', 'assignment_digest', 'artifact_ref', 'receipt_digest',
  ])) {
    const ref = value.artifact_ref;
    return value.schema_version === 'wuji.worker-settlement.v1'
      && value.kind === kind && value.assignment_digest === record.assignment_digest
      && exactKeys(ref, ['id', 'version', 'sha256']) && text(ref.id)
      && revision.test(ref.version) && typeof ref.sha256 === 'string'
      && /^[a-f0-9]{64}$/.test(ref.sha256)
      && typeof value.receipt_digest === 'string'
      && /^[a-f0-9]{64}$/.test(value.receipt_digest);
  }
  return false;
}
function observation(record, kind, processRecord, reason) {
  const body = { receipt_id: nonce(), identity: record.assignment.identity,
    operation_id: record.operation_id, environment_ref: record.receiver.environment_ref,
    pod_uid: record.receiver.pod_uid, kind, observed_at: now(), process: processRecord, reason };
  const source_receipt = canonical(body);
  return { ...body, source_receipt, source_digest: digest(body) };
}

export class NodeSupervisor {
  static async open(options) { return new NodeSupervisor(options); }

  constructor({ inboxDir, receiver, profiles, authorize, bootstrap = async () => {},
    persistResults = null, fault = async () => {}, spawnWaitMs = 3000,
    maxLogBytes = 1048576 }) {
    if (!exactKeys(receiver, receiverKeys) || receiverKeys.some(k => !text(receiver[k]))
        || !revision.test(receiver.runtime_attempt)) throw new SupervisorError('INVALID_RECEIVER', 422);
    if (typeof authorize !== 'function' || typeof bootstrap !== 'function'
        || persistResults !== null && typeof persistResults !== 'function'
        || typeof fault !== 'function') {
      throw new SupervisorError('AUTHORIZATION_ADAPTER_REQUIRED', 503);
    }
    if (!Number.isSafeInteger(spawnWaitMs) || spawnWaitMs < 1 || spawnWaitMs > 30000
        || !Number.isSafeInteger(maxLogBytes) || maxLogBytes < 0 || maxLogBytes > 16777216) {
      throw new SupervisorError('INVALID_PROCESS_LIMIT', 422);
    }
    this.profiles = new Map();
    for (const [id, input] of Object.entries(profiles ?? {})) {
      const p = parseJson(canonical(input));
      if (!text(id) || !isAbsolute(p.command ?? '') || !isAbsolute(p.cwd ?? '')
          || !Array.isArray(p.args) || !p.args.every(a => typeof a === 'string')
          || !p.env || Array.isArray(p.env) || !Object.entries(p.env).every(([k, v]) => /^[A-Za-z_][A-Za-z0-9_]*$/.test(k) && typeof v === 'string')
          || !Array.isArray(p.workKinds) || !p.workKinds.length || p.workKinds.some(k => !['reason', 'explore', 'report'].includes(k))) {
        throw new SupervisorError('INVALID_LAUNCH_PROFILE', 422);
      }
      this.profiles.set(id, p);
    }
    this.receiver = parseJson(canonical(receiver));
    this.authorize = authorize; this.bootstrap = bootstrap;
    this.persistResults = persistResults; this.fault = fault;
    this.spawnWaitMs = spawnWaitMs; this.maxLogBytes = maxLogBytes;
    this.inbox = new DurableInbox(inboxDir, this.receiver);
    this.queue = Promise.resolve(); this.closing = false;
  }

  serial(action) {
    if (this.closing) return Promise.reject(new SupervisorError('RECEIVER_CLOSED', 503));
    const result = this.queue.then(action);
    this.queue = result.catch(() => {}); return result;
  }

  async permit(action, record, auth, controlId = null) {
    const request = { action, assignment: record.assignment, assignment_digest: record.assignment_digest,
      receiver: this.receiver, control_operation_id: controlId, auth };
    // Give adapters a detached document; they cannot mutate the frozen operation.
    const grant = await this.authorize({ ...parseJson(canonical({ ...request, auth: null })), auth });
    if (!grant || typeof grant !== 'object' || grant.action !== action || !text(grant.subject)
        || !equal(grant.identity, record.assignment.identity) || !equal(grant.receiver, this.receiver)
        || grant.assignment_digest !== record.assignment_digest || typeof grant.execution_allowed !== 'boolean'
        || typeof grant.valid_until !== 'string' || !Number.isFinite(Date.parse(grant.valid_until))
        || Date.parse(grant.valid_until) <= Date.now() || (action === 'start' && !grant.execution_allowed)) {
      throw new SupervisorError('STALE_EXECUTION', 403);
    }
    return grant;
  }

  assignment(request) {
    if (!exactKeys(request, ['start_operation_id', 'assignment', 'profile_id'])) throw new SupervisorError('INVALID_START', 422);
    const assignment = parseJson(canonical(request.assignment));
    validateIdentity(assignment.identity);
    if (!text(request.start_operation_id) || assignment.operation_id !== request.start_operation_id
        || !text(assignment.snapshot_id) || !Array.isArray(assignment.profile_refs)
        || !assignment.profile_refs.includes(request.profile_id)
        || assignment.identity.receiver_id !== this.receiver.receiver_id
        || assignment.identity.runtime_attempt !== this.receiver.runtime_attempt) {
      throw new SupervisorError('STALE_EXECUTION', 409);
    }
    return { operation_id: request.start_operation_id, assignment, assignment_digest: digest(assignment),
      receiver: this.receiver, profile_id: request.profile_id };
  }

  receipt(record) {
    return parseJson(canonical({ operation_id: record.operation_id, identity: record.assignment.identity,
      receiver: record.receiver, assignment_digest: record.assignment_digest, profile_id: record.profile_id,
      state: record.state, observation: record.observation }));
  }

  setState(record, state, proof, reason) {
    const processRecord = proof?.process ?? record.observation?.process ?? null;
    if (record.state === state && equal(record.observation?.process ?? null, processRecord)) return record;
    record.state = state;
    const kind = state === 'running' ? 'started' : state;
    record.observation = observation(record, kind, processRecord, reason);
    this.inbox.save(record); return record;
  }

  validateProof(record, proof) {
    if (!proof || proof.launch_id !== record.launch_id || !equal(proof.identity, record.assignment.identity)
        || !equal(proof.receiver, this.receiver) || proof.assignment_digest !== record.assignment_digest
        || !text(proof.guardian_birth_id) || !Number.isSafeInteger(proof.guardian_pid)
        || !['prepared', 'running', 'exited', 'not_started'].includes(proof.state)) throw new SupervisorError('INVALID_PROCESS_PROOF');
    const p = proof.process;
    if (['running', 'exited'].includes(proof.state) && (!p || !Number.isSafeInteger(p.pid) || p.pid < 1
        || typeof p.birth_id !== 'string' || !p.birth_id.startsWith(`${record.launch_id}:${proof.guardian_birth_id}:`)
        || !Number.isFinite(Date.parse(p.started_at)))) throw new SupervisorError('INVALID_PROCESS_PROOF');
    if (proof.state === 'exited' && (!Number.isSafeInteger(p.exit_code)
        || !Number.isFinite(Date.parse(p.exited_at)) || Date.parse(p.exited_at) < Date.parse(p.started_at))) throw new SupervisorError('INVALID_PROCESS_PROOF');
    if (['prepared', 'not_started'].includes(proof.state) && p !== null) throw new SupervisorError('INVALID_PROCESS_PROOF');
    return proof;
  }

  async persistProducedResults(record) {
    const directory = join(record.directory, 'worker');
    const hasResult = existsSync(join(directory, 'result-request.json'));
    const hasSdk = existsSync(join(directory, 'sdk-request.json'));
    if (!hasResult && !hasSdk) return;
    const kind = hasResult ? 'result' : 'archive';
    const settlement = await this.persistResults?.({
      assignment: parseJson(canonical(record.assignment)),
      directory,
    });
    if (!durableSettlement(settlement, record, kind)) {
      throw new SupervisorError('RESULT_PERSISTENCE_UNCONFIRMED', 503);
    }
    return settlement;
  }

  async observe(record) {
    if (['exited', 'not_started'].includes(record.state)) return record;
    let lastKnownProof = null;
    try {
      const stored = readProof(join(record.directory, 'process.json'), record.secret);
      if (stored) {
        this.validateProof(record, stored);
        if (stored.process) lastKnownProof = stored;
        if (['exited', 'not_started'].includes(stored.state)) {
          await this.persistProducedResults(record);
          return this.setState(record, stored.state, stored, stored.reason);
        }
      }
      const answer = await guardianRequest(record.socket_path, record.secret, record.launch_id, 'query');
      const proof = this.validateProof(record, answer.proof);
      if (proof.process) lastKnownProof = proof;
      if (proof.state !== 'prepared') {
        await this.persistProducedResults(record);
        return this.setState(record, proof.state, proof, proof.reason);
      }
    } catch {
      // Absence, a dead guardian, a reused PID, or invalid proof cannot release.
    }
    return this.setState(
      record, 'unknown', lastKnownProof, 'process_truth_unresolved',
    );
  }

  start(request, auth) {
    return this.serial(async () => {
      const proposed = this.assignment(request);
      // Read permission is rechecked even before returning an old receipt.
      await this.permit('query', proposed, auth);
      const old = this.inbox.get(proposed.operation_id);
      if (old) {
        if (old.assignment_digest !== proposed.assignment_digest || old.profile_id !== proposed.profile_id) throw new SupervisorError('INPUT_DIGEST_CONFLICT');
        return this.receipt(await this.observe(old));
      }
      const profile = this.profiles.get(proposed.profile_id);
      if (!profile || !profile.workKinds.includes(proposed.assignment.work_kind)) throw new SupervisorError('UNREGISTERED_LAUNCH_PROFILE', 403);
      await this.permit('start', proposed, auth);
      const launch_id = nonce(), secret = nonce();
      const directory = join(this.inbox.directory, 'launches', launch_id);
      mkdirSync(directory, { recursive: true, mode: 0o700 });
      const workerDirectory = join(directory, 'worker');
      mkdirSync(workerDirectory, { mode: 0o700 });
      durableWrite(join(workerDirectory, 'assignment.json'), proposed.assignment);
      await this.bootstrap({ assignment: parseJson(canonical(proposed.assignment)), directory: workerDirectory });
      await this.permit('start', proposed, auth);
      // Short Unix socket path works on both Darwin and Linux; mkdtemp is 0700.
      const socket_path = join(mkdtempSync('/tmp/wuji-maf-'), 'control.sock');
      const record = { ...proposed, directory, socket_path, launch_id, secret,
        profile_digest: digest(profile), state: 'prepared', observation: null, prepared_at: now() };
      durableWrite(join(directory, 'launch.json'), { launch_id, secret, socket_path,
        identity: proposed.assignment.identity, receiver: this.receiver, assignment_digest: proposed.assignment_digest,
        command: profile.command, args: profile.args, cwd: profile.cwd,
        env: { ...profile.env, WUJI_WORKER_ASSIGNMENT_FILE: join(workerDirectory, 'assignment.json'),
          WUJI_WORKER_BOOTSTRAP_DIRECTORY: workerDirectory }, max_log_bytes: this.maxLogBytes });
      await this.fault('before_prepared', { operation_id: record.operation_id });
      this.inbox.insert(record); // FULL-synchronous commit before any spawn
      await this.fault('after_prepared_before_spawn', { operation_id: record.operation_id });
      try { await this.permit('start', record, auth); }
      catch (error) {
        this.setState(record, 'not_started', null, 'permit_revoked_before_spawn'); throw error;
      }
      let launcherError = false;
      try {
        const guardian = spawn(process.execPath, [fileURLToPath(new URL('./guardian.mjs', import.meta.url)), directory], {
          detached: true, stdio: 'ignore', env: {}, shell: false,
        });
        guardian.once('error', () => { launcherError = true; });
        guardian.unref();
      } catch { launcherError = true; }
      let proof = null;
      const deadline = Date.now() + this.spawnWaitMs;
      do {
        if (launcherError) return this.receipt(this.setState(record, 'not_started', null, 'guardian_os_spawn_failed'));
        try {
          proof = readProof(join(directory, 'process.json'), secret);
          if (proof) this.validateProof(record, proof);
          if (proof && proof.state !== 'prepared') break;
        } catch { proof = null; }
        await delay(15);
      } while (Date.now() < deadline);
      if (proof?.process) await this.fault('after_spawn_before_running_receipt', { operation_id: record.operation_id });
      // A durable birth alone proves past spawn, not current liveness.
      const observed = await this.observe(record);
      if (observed.observation?.process) await this.fault('after_running_before_response', { operation_id: record.operation_id });
      return this.receipt(observed);
    });
  }

  query(operationId, auth) {
    return this.serial(async () => {
      const record = this.inbox.get(operationId);
      if (!record) {
        // The server authenticated the caller already. No negative process
        // evidence or not_started receipt can be inferred from missing inbox.
        throw new SupervisorError('OPERATION_NOT_FOUND', 404);
      }
      await this.permit('query', record, auth);
      return this.receipt(await this.observe(record));
    });
  }

  control(operationId, request, auth) {
    return this.serial(async () => {
      if (!exactKeys(request, ['control_operation_id', 'action', 'identity']) || !text(request.control_operation_id)) throw new SupervisorError('INVALID_CONTROL', 422);
      const record = this.inbox.get(operationId);
      if (!record) throw new SupervisorError('OPERATION_NOT_FOUND', 404);
      validateIdentity(request.identity);
      if (!equal(request.identity, record.assignment.identity)) throw new SupervisorError('STALE_EXECUTION');
      if (!['stop', 'stop_after_current'].includes(request.action)) throw new SupervisorError('INVALID_CONTROL', 422);
      await this.permit(request.action, record, auth, request.control_operation_id);
      if (request.action === 'stop_after_current') throw new SupervisorError('COOPERATIVE_CONTROL_UNAVAILABLE', 503);
      const inputDigest = digest({ operation_id: operationId, ...request });
      const old = this.inbox.getControl(request.control_operation_id);
      if (old && old.input_digest !== inputDigest) throw new SupervisorError('INPUT_DIGEST_CONFLICT');
      const receipt = old?.receipt ?? { operation_id: request.control_operation_id,
        start_operation_id: operationId, identity: record.assignment.identity, status: 'accepted', accepted_at: now() };
      if (!old) this.inbox.control(request.control_operation_id, inputDigest, receipt);
      // Idempotent intent redelivery is allowed; the guardian uses its live
      // ChildProcess handle. Neither accepted nor a successful kill means exit.
      if (!['exited', 'not_started'].includes(record.state)) {
        try { await guardianRequest(record.socket_path, record.secret, record.launch_id, 'stop', request.control_operation_id); }
        catch { /* retain unresolved process and capacity */ }
      }
      return { ...receipt, execution: this.receipt(await this.observe(record)) };
    });
  }

  createServer({ authenticate, maxBodyBytes = 1048576, tls = null } = {}) {
    if (typeof authenticate !== 'function') throw new SupervisorError('AUTHENTICATOR_REQUIRED', 503);
    if (tls !== null && (!tls.cert || !tls.key)) throw new SupervisorError('INVALID_TLS_CONFIGURATION', 422);
    const handle = async (request, response) => {
      try {
        const auth = await authenticate(request);
        if (auth === null || auth === undefined || auth === false) throw new SupervisorError('UNAUTHENTICATED', 401);
        const path = new URL(request.url, 'http://receiver.invalid').pathname;
        const match = path.match(/^\/operations\/([^/]+)(\/control)?$/);
        if (!match) throw new SupervisorError('NOT_FOUND', 404);
        const id = decodeURIComponent(match[1]);
        if (!text(id)) throw new SupervisorError('INVALID_OPERATION', 422);
        let result;
        if (request.method === 'GET' && !match[2]) result = await this.query(id, auth);
        else {
          const chunks = []; let size = 0;
          for await (const chunk of request) {
            size += chunk.length;
            if (size > maxBodyBytes) throw new SupervisorError('BODY_TOO_LARGE', 413);
            chunks.push(chunk);
          }
          const body = parseJson(Buffer.concat(chunks).toString('utf8'));
          if (request.method === 'PUT' && !match[2]) {
            if (!exactKeys(body, ['assignment', 'profile_id'])) throw new SupervisorError('INVALID_START', 422);
            result = await this.start({ start_operation_id: id, ...body }, auth);
          } else if (request.method === 'POST' && match[2]) result = await this.control(id, body, auth);
          else throw new SupervisorError('METHOD_NOT_ALLOWED', 405);
        }
        response.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
        response.end(canonical(result));
      } catch (error) {
        response.writeHead(error instanceof SupervisorError ? error.status : 503,
          { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
        response.end(canonical({ code: error instanceof SupervisorError ? error.code : 'RECEIVER_UNAVAILABLE' }));
      }
    };
    const server = tls === null ? createServer(handle) : createTlsServer({ ...tls, minVersion: 'TLSv1.2' }, handle);
    server.requestTimeout = 15000; server.headersTimeout = 10000;
    return server;
  }

  async close() {
    if (this.closing) return;
    this.closing = true; await this.queue; this.inbox.close();
  }
}

// Explicit deployment factory only. Importing the class never starts a service.
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const index = process.argv.indexOf('--factory');
  if (index < 0 || !process.argv[index + 1]) throw new Error('deployment --factory /absolute/module.mjs required');
  const module = await import(pathToFileURL(resolve(process.argv[index + 1])).href);
  const configuration = await module.buildSupervisor();
  const supervisor = await NodeSupervisor.open(configuration);
  const server = supervisor.createServer({ authenticate: configuration.authenticate,
    tls: configuration.tls ?? null, maxBodyBytes: configuration.maxBodyBytes ?? 1048576 });
  server.listen(configuration.port, configuration.host ?? '127.0.0.1');
  for (const signal of ['SIGINT', 'SIGTERM']) process.once(signal, () => {
    server.close(() => supervisor.close());
  });
}
