import { DatabaseSync } from 'node:sqlite';
import { chmodSync, lstatSync, mkdirSync, realpathSync } from 'node:fs';
import { join } from 'node:path';
import { canonical, equal, parseJson, SupervisorError } from './protocol.mjs';

export class DurableInbox {
  constructor(directory, receiver) {
    mkdirSync(directory, { recursive: true, mode: 0o700 });
    if (lstatSync(directory).isSymbolicLink()) throw new SupervisorError('UNSAFE_INBOX');
    this.directory = realpathSync(directory);
    chmodSync(this.directory, 0o700);
    try {
      // This separate, lifetime transaction is an OS-released exclusive lock.
      // The metadata/inbox database remains independently durable after each write.
      this.owner = new DatabaseSync(join(this.directory, 'owner.sqlite'));
      this.owner.exec('PRAGMA busy_timeout=0; BEGIN EXCLUSIVE');
      this.db = new DatabaseSync(join(this.directory, 'inbox.sqlite'));
      this.db.exec(`PRAGMA journal_mode=DELETE; PRAGMA synchronous=FULL;
        CREATE TABLE IF NOT EXISTS metadata (id INTEGER PRIMARY KEY CHECK(id=1), receiver TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS operations (operation_id TEXT PRIMARY KEY, run_key TEXT UNIQUE NOT NULL, body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS controls (operation_id TEXT PRIMARY KEY, input_digest TEXT NOT NULL, body TEXT NOT NULL);`);
      chmodSync(join(this.directory, 'owner.sqlite'), 0o600);
      chmodSync(join(this.directory, 'inbox.sqlite'), 0o600);
      const stored = this.db.prepare('SELECT receiver FROM metadata WHERE id=1').get();
      if (stored && !equal(parseJson(stored.receiver), receiver)) throw new SupervisorError('RECEIVER_IDENTITY_CONFLICT');
      if (!stored) this.db.prepare('INSERT INTO metadata VALUES(1,?)').run(canonical(receiver));
    } catch (error) {
      this.db?.close(); this.owner?.close();
      if (error instanceof SupervisorError) throw error;
      throw new SupervisorError('INBOX_UNAVAILABLE_OR_OWNED', 503);
    }
  }
  get(id) {
    const row = this.db.prepare('SELECT body FROM operations WHERE operation_id=?').get(id);
    return row ? parseJson(row.body) : null;
  }
  insert(record) {
    this.db.prepare('INSERT INTO operations VALUES(?,?,?)').run(record.operation_id, canonical([
      record.assignment.identity.tenant_id, record.assignment.identity.project_id,
      record.assignment.identity.task_id, record.assignment.identity.agent_run_id,
    ]), canonical(record));
  }
  save(record) { this.db.prepare('UPDATE operations SET body=? WHERE operation_id=?').run(canonical(record), record.operation_id); }
  getControl(id) {
    const row = this.db.prepare('SELECT input_digest,body FROM controls WHERE operation_id=?').get(id);
    return row ? { input_digest: row.input_digest, receipt: parseJson(row.body) } : null;
  }
  control(id, inputDigest, receipt) {
    this.db.prepare('INSERT INTO controls VALUES(?,?,?)').run(id, inputDigest, canonical(receipt));
  }
  close() { this.db.close(); this.owner.close(); }
}
