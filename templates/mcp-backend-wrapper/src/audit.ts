/**
 * Append-only audit log: one JSON line per tool call, success or failure.
 *
 * When an agent can write to your systems, you want to answer "what did it do,
 * and when?" without guessing. Never throws: a failing log must not break the call.
 */
import { appendFileSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { randomUUID } from 'node:crypto';

export interface AuditRecord {
  tool: string;
  action: 'read' | 'write';
  success: boolean;
  summary?: string;
  error?: string;
}

export type Writer = (path: string, line: string) => void;

const defaultWriter: Writer = (path, line) => {
  mkdirSync(dirname(path), { recursive: true });
  appendFileSync(path, line, 'utf8');
};

export function audit(path: string, rec: AuditRecord, writer: Writer = defaultWriter): void {
  const line = JSON.stringify({ ts: new Date().toISOString(), trace_id: randomUUID(), ...rec }) + '\n';
  try {
    writer(path, line);
  } catch (err) {
    process.stderr.write(`[audit] append failed: ${(err as Error).message}\n`);
  }
}
