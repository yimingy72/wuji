// Registered receiver -> actual controller ports. No process/Agent loop here.
import { timingSafeEqual } from 'node:crypto';
import { request as httpRequest } from 'node:http';
import { request as httpsRequest } from 'node:https';
import { constants, closeSync, fstatSync, fsyncSync, linkSync, lstatSync,
  openSync, readSync, unlinkSync, writeFileSync } from 'node:fs';
import { isAbsolute, join } from 'node:path';
import { canonical, digest, equal, nonce, parseJson, SupervisorError } from './protocol.mjs';

const receiverKeys = ['receiver_id', 'runtime_attempt', 'environment_ref', 'pod_uid'];
const bootstrapKeys = ['assignment', 'assignment_digest', 'receiver', 'run_credential',
  'public_key_pem', 'issuer', 'audience', 'host_origin', 'model_gate_url', 'tool_gate_url',
  'wait_timeout_seconds', 'transport_timeout_seconds', 'max_transport_bytes'];
const bounded = (value, maximum = 256) => typeof value === 'string' && value.length > 0 && value.length <= maximum;
const keys = (value, names) => value && typeof value === 'object' && !Array.isArray(value)
  && Object.keys(value).length === names.length && names.every(name => Object.hasOwn(value, name));

function privateRead(path, maximum) {
  let fd;
  try { fd = openSync(path, constants.O_RDONLY | constants.O_NOFOLLOW); }
  catch (error) { if (error.code === 'ENOENT') return null; throw error; }
  try {
    const info = fstatSync(fd);
    if (!info.isFile() || (info.mode & 0o077) || info.size > maximum) {
      throw new SupervisorError('INVALID_WORKER_ARCHIVE', 422);
    }
    const output = Buffer.alloc(info.size + 1);
    let offset = 0, count;
    while (offset < output.length && (count = readSync(fd, output, offset, output.length - offset, null))) offset += count;
    if (offset !== info.size) throw new SupervisorError('INVALID_WORKER_ARCHIVE', 422);
    return output.subarray(0, offset);
  } finally { closeSync(fd); }
}

function privateSave(path, data, directory, maximum) {
  if (data.length > maximum) throw new SupervisorError('BODY_TOO_LARGE', 413);
  const temporary = join(directory, `.${nonce()}.bridge-tmp`);
  const fd = openSync(temporary, 'wx', 0o600);
  try { writeFileSync(fd, data); fsyncSync(fd); }
  finally { closeSync(fd); }
  try {
    try { linkSync(temporary, path); }
    catch (error) {
      if (error.code !== 'EEXIST') throw error;
      const old = privateRead(path, maximum);
      if (!old || !old.equals(data)) throw new SupervisorError('INPUT_DIGEST_CONFLICT', 409);
    }
    const parent = openSync(directory, 'r');
    try { fsyncSync(parent); } finally { closeSync(parent); }
  } finally { unlinkSync(temporary); }
}

export class ControllerAdapter {
  constructor({ origin, authorization, receiver, timeoutMs = 10000, maxResponseBytes = 1048576,
    maxRequestBytes = 67108864 }) {
    const target = new URL(origin);
    const local = ['localhost', '127.0.0.1', '[::1]'].includes(target.hostname);
    if (!['http:', 'https:'].includes(target.protocol) || target.username || target.password
        || target.search || target.hash || target.pathname !== '/'
        || (target.protocol === 'http:' && !local) || typeof authorization !== 'function'
        || !keys(receiver, receiverKeys) || receiverKeys.some(k => !bounded(receiver[k]))
        || !/^(0|[1-9][0-9]*)$/.test(receiver.runtime_attempt)
        || !Number.isSafeInteger(timeoutMs) || timeoutMs < 1 || timeoutMs > 60000
        || !Number.isSafeInteger(maxResponseBytes) || maxResponseBytes < 1 || maxResponseBytes > 67108864
        || !Number.isSafeInteger(maxRequestBytes) || maxRequestBytes < 1 || maxRequestBytes > 67108864) {
      throw new SupervisorError('INVALID_CONTROLLER_CONFIGURATION', 422);
    }
    this.origin = target.origin;
    this.authorization = authorization;
    this.receiver = parseJson(canonical(receiver));
    this.timeoutMs = timeoutMs;
    this.maxResponseBytes = maxResponseBytes;
    this.maxRequestBytes = maxRequestBytes;
    this.authorize = this.authorize.bind(this);
    this.bootstrap = this.bootstrap.bind(this);
    this.persistResults = this.persistResults.bind(this);
    this.authenticate = this.authenticate.bind(this);
  }

  async token() {
    const token = await this.authorization();
    if (!bounded(token, 16384) || /\s/.test(token)) throw new SupervisorError('UNAUTHENTICATED', 401);
    return token;
  }

  async authenticate(request) {
    // Possession check for the fixed controller/receiver channel only; actual
    // JWT verification and canonical assignment authority are on the controller.
    const entries = [];
    for (let i = 0; i < request.rawHeaders.length; i += 2) {
      if (request.rawHeaders[i].toLowerCase() === 'authorization') entries.push(request.rawHeaders[i + 1]);
    }
    if (entries.length !== 1 || !entries[0].startsWith('Bearer ')) throw new SupervisorError('UNAUTHENTICATED', 401);
    const supplied = Buffer.from(entries[0].slice(7)), expected = Buffer.from(await this.token());
    if (supplied.length !== expected.length || !timingSafeEqual(supplied, expected)) {
      throw new SupervisorError('UNAUTHENTICATED', 401);
    }
    return supplied.toString();
  }

  async post(action, body, token = null) {
    if (!['receiver-authorize', 'receiver-bootstrap', 'receiver-replay', 'receiver-archive'].includes(action)) {
      throw new SupervisorError('INVALID_CONTROLLER_ACTION', 422);
    }
    const data = Buffer.isBuffer(body) ? body : Buffer.from(canonical(body));
    if (data.length > this.maxRequestBytes) throw new SupervisorError('BODY_TOO_LARGE', 413);
    const bearer = token ?? await this.token();
    const url = new URL(`${this.origin}/internal/v2/worker-host/${action}`);
    return new Promise((resolve, reject) => {
      let settled = false;
      const finish = (error, value) => {
        if (settled) return;
        settled = true; clearTimeout(timer);
        if (error) reject(error); else resolve(value);
      };
      const send = url.protocol === 'https:' ? httpsRequest : httpRequest;
      const req = send(url, { method: 'POST', agent: false,
        headers: { Authorization: `Bearer ${bearer}`, 'Content-Type': 'application/json',
          'Content-Length': data.length, Accept: 'application/json', 'Accept-Encoding': 'identity' } }, res => {
        if (res.statusCode !== 200 || res.headers['content-encoding'] && res.headers['content-encoding'] !== 'identity') {
          res.destroy();
          return finish(new SupervisorError('CONTROLLER_REQUEST_REJECTED', res.statusCode === 401 ? 401 : 503));
        }
        const chunks = []; let size = 0;
        res.on('data', chunk => {
          size += chunk.length;
          if (size > this.maxResponseBytes) {
            res.destroy(); finish(new SupervisorError('CONTROLLER_RESPONSE_TOO_LARGE', 503));
          } else chunks.push(chunk);
        });
        res.on('error', () => finish(new SupervisorError('CONTROLLER_RESPONSE_UNKNOWN', 503)));
        res.on('aborted', () => finish(new SupervisorError('CONTROLLER_RESPONSE_UNKNOWN', 503)));
        res.on('end', () => {
          try { finish(null, parseJson(Buffer.concat(chunks).toString('utf8'))); }
          catch { finish(new SupervisorError('INVALID_CONTROLLER_RESPONSE', 503)); }
        });
      });
      const timer = setTimeout(() => {
        req.destroy(); finish(new SupervisorError('CONTROLLER_RESPONSE_UNKNOWN', 503));
      }, this.timeoutMs);
      req.on('error', () => finish(new SupervisorError('CONTROLLER_RESPONSE_UNKNOWN', 503)));
      req.end(data);
    });
  }

  async authorize({ action, assignment, assignment_digest, receiver, control_operation_id, auth }) {
    const token = await this.token();
    // A direct Node call must pass the same authenticated service channel as
    // createServer. Arbitrary truthy objects are not authorization assertions.
    if (typeof auth !== 'string' || Buffer.byteLength(auth) !== Buffer.byteLength(token)
        || !timingSafeEqual(Buffer.from(auth), Buffer.from(token))) {
      throw new SupervisorError('UNAUTHENTICATED', 401);
    }
    if (!equal(receiver, this.receiver) || assignment_digest !== digest(assignment)) {
      throw new SupervisorError('STALE_EXECUTION', 409);
    }
    return this.post('receiver-authorize', { action, assignment, assignment_digest,
      receiver: this.receiver, control_operation_id: control_operation_id ?? null }, token);
  }

  directory(directory) {
    if (!isAbsolute(directory)) throw new SupervisorError('INVALID_WORKER_DIRECTORY', 422);
    const info = lstatSync(directory);
    if (!info.isDirectory() || info.isSymbolicLink() || info.mode & 0o077) {
      throw new SupervisorError('INVALID_WORKER_DIRECTORY', 422);
    }
  }

  async bootstrap({ assignment, directory }) {
    this.directory(directory);
    const answer = await this.post('receiver-bootstrap', { assignment });
    if (!keys(answer, bootstrapKeys) || !equal(answer.assignment, assignment)
        || answer.assignment_digest !== digest(assignment) || !equal(answer.receiver, this.receiver)
        || !bounded(answer.run_credential, 16384) || /\s/.test(answer.run_credential)
        || !bounded(answer.public_key_pem, 16384) || answer.public_key_pem.includes('PRIVATE KEY')
        || !Number.isSafeInteger(answer.max_transport_bytes) || answer.max_transport_bytes > this.maxRequestBytes) {
      throw new SupervisorError('INVALID_WORKER_BOOTSTRAP', 422);
    }
    privateSave(join(directory, 'bridge.json'), Buffer.from(canonical(answer)), directory, this.maxResponseBytes);
  }

  async persistResults({ assignment, directory }) {
    this.directory(directory);
    // Never parse/re-encode SDK/raw/receipt content with JS Number semantics.
    // Controller's strict generated DTOs validate the original exact request.
    const result = privateRead(join(directory, 'result-request.json'), this.maxRequestBytes);
    const archive = result === null ? privateRead(join(directory, 'sdk-request.json'), this.maxRequestBytes) : null;
    const body = result ?? archive;
    if (body === null) return null;
    let embedded;
    try { embedded = JSON.parse(body.toString('utf8')).assignment; }
    catch { throw new SupervisorError('INVALID_WORKER_ARCHIVE', 422); }
    if (!equal(embedded, assignment)) throw new SupervisorError('STALE_EXECUTION', 409);
    const receipt = await this.post(result === null ? 'receiver-archive' : 'receiver-replay', body);
    // No local fake ack and no derivation of process state from result status.
    return receipt;
  }
}

export function mafProfile({ pythonExecutable, cwd, env = {}, workKinds = ['explore'] }) {
  if (!isAbsolute(pythonExecutable) || !isAbsolute(cwd)
      || !keys(env, Object.keys(env)) || Object.keys(env).some(key => !['PATH', 'PYTHONPATH',
        'PYTHONNOUSERSITE', 'PYTHONDONTWRITEBYTECODE', 'LANG', 'LC_ALL', 'TZ'].includes(key))
      || Object.values(env).some(value => typeof value !== 'string')) {
    throw new SupervisorError('INVALID_LAUNCH_PROFILE', 422);
  }
  return { command: pythonExecutable, args: ['-m', 'wuji_maf_worker.child_entrypoint'],
    cwd, env: { ...env, PYTHONNOUSERSITE: '1' }, workKinds };
}
