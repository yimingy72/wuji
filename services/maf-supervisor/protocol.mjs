import { createHash, createHmac, randomBytes, timingSafeEqual } from 'node:crypto';
import { closeSync, fsyncSync, openSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
import { dirname } from 'node:path';
import { createConnection } from 'node:net';

export class SupervisorError extends Error {
  constructor(code, status = 409) { super(code); this.code = code; this.status = status; }
}

export function canonical(value, depth = 0) {
  if (depth > 64) throw new SupervisorError('INVALID_JSON', 422);
  if (value === null || typeof value === 'boolean' || typeof value === 'string') return JSON.stringify(value);
  if (typeof value === 'number' && Number.isSafeInteger(value)) return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(v => canonical(v, depth + 1)).join(',')}]`;
  if (value && Object.getPrototypeOf(value) === Object.prototype) {
    const order = (a, b) => {
      const x = Array.from(a, c => c.codePointAt(0)), y = Array.from(b, c => c.codePointAt(0));
      for (let i = 0; i < Math.min(x.length, y.length); i++) if (x[i] !== y[i]) return x[i] - y[i];
      return x.length - y.length;
    };
    return `{${Object.keys(value).sort(order).map(k => `${JSON.stringify(k)}:${canonical(value[k], depth + 1)}`).join(',')}}`;
  }
  throw new SupervisorError('INVALID_JSON', 422);
}

// Duplicate keys are rejected before JSON.parse can silently discard them.
export function parseJson(text) {
  let offset = 0;
  const space = () => { while (/\s/.test(text[offset] ?? '') && offset < text.length) offset++; };
  function string() {
    const start = offset++;
    while (offset < text.length) {
      if (text[offset++] === '"') return JSON.parse(text.slice(start, offset));
      if (text[offset - 1] === '\\') offset++;
    }
    throw new SupervisorError('INVALID_JSON', 422);
  }
  function value(depth) {
    if (depth > 64) throw new SupervisorError('INVALID_JSON', 422);
    space();
    if (text[offset] === '"') return string();
    if (text[offset] === '{') {
      offset++; space(); const seen = new Set();
      if (text[offset] === '}') { offset++; return; }
      while (offset < text.length) {
        space(); if (text[offset] !== '"') throw new SupervisorError('INVALID_JSON', 422);
        const key = string();
        if (seen.has(key)) throw new SupervisorError('DUPLICATE_JSON_KEY', 422);
        seen.add(key); space();
        if (text[offset++] !== ':') throw new SupervisorError('INVALID_JSON', 422);
        value(depth + 1); space();
        if (text[offset] === '}') { offset++; return; }
        if (text[offset++] !== ',') throw new SupervisorError('INVALID_JSON', 422);
      }
    } else if (text[offset] === '[') {
      offset++; space(); if (text[offset] === ']') { offset++; return; }
      while (offset < text.length) {
        value(depth + 1); space(); if (text[offset] === ']') { offset++; return; }
        if (text[offset++] !== ',') throw new SupervisorError('INVALID_JSON', 422);
      }
    } else {
      const token = text.slice(offset).match(/^(?:true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)/);
      if (token) { offset += token[0].length; return; }
    }
    throw new SupervisorError('INVALID_JSON', 422);
  }
  try {
    value(0); space(); if (offset !== text.length) throw new Error();
    const parsed = JSON.parse(text); canonical(parsed); return parsed;
  } catch (error) {
    if (error instanceof SupervisorError) throw error;
    throw new SupervisorError('INVALID_JSON', 422);
  }
}

export const digest = value => createHash('sha256').update(canonical(value)).digest('hex');
export const nonce = () => randomBytes(32).toString('hex');
export const equal = (a, b) => canonical(a) === canonical(b);
export const now = () => new Date().toISOString();

export function durableWrite(path, value) {
  const temporary = `${path}.${nonce()}.tmp`;
  const fd = openSync(temporary, 'wx', 0o600);
  try { writeFileSync(fd, canonical(value)); fsyncSync(fd); } finally { closeSync(fd); }
  renameSync(temporary, path);
  const directory = openSync(dirname(path), 'r');
  try { fsyncSync(directory); } finally { closeSync(directory); }
}

export function signed(body, secret) {
  return { body, signature: createHmac('sha256', secret).update(canonical(body)).digest('hex') };
}

export function verified(document, secret) {
  if (!document || typeof document.signature !== 'string' || !/^[a-f0-9]{64}$/.test(document.signature)) throw new SupervisorError('INVALID_PROCESS_PROOF');
  const expected = signed(document.body, secret).signature;
  if (!timingSafeEqual(Buffer.from(expected, 'hex'), Buffer.from(document.signature, 'hex'))) throw new SupervisorError('INVALID_PROCESS_PROOF');
  return document.body;
}

export function readProof(path, secret) {
  try { return verified(parseJson(readFileSync(path, 'utf8')), secret); }
  catch (error) { if (error.code === 'ENOENT') return null; throw error; }
}

export function guardianRequest(path, secret, launchId, action, controlId = null) {
  return new Promise((resolve, reject) => {
    const challenge = nonce(); let body = '', settled = false;
    const socket = createConnection(path);
    const finish = (error, response) => {
      if (settled) return; settled = true; socket.destroy();
      if (error) reject(error); else resolve(response);
    };
    socket.setTimeout(1500, () => finish(new SupervisorError('GUARDIAN_UNREACHABLE', 503)));
    socket.on('error', () => finish(new SupervisorError('GUARDIAN_UNREACHABLE', 503)));
    socket.on('end', () => finish(new SupervisorError('GUARDIAN_UNREACHABLE', 503)));
    socket.on('connect', () => socket.write(canonical(signed({ launch_id: launchId, action, control_id: controlId, challenge }, secret)) + '\n'));
    socket.on('data', chunk => {
      body += chunk.toString('utf8');
      if (Buffer.byteLength(body) > 65536) return finish(new SupervisorError('INVALID_PROCESS_PROOF'));
      if (!body.includes('\n')) return;
      try {
        const answer = verified(parseJson(body.slice(0, body.indexOf('\n'))), secret);
        if (answer.challenge !== challenge || answer.launch_id !== launchId) throw new SupervisorError('INVALID_PROCESS_PROOF');
        finish(null, answer);
      } catch (error) { finish(error); }
    });
  });
}
