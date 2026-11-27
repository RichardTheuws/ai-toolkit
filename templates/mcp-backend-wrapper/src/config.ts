/**
 * Runtime configuration, all from environment variables.
 *
 * Read lazily (on first call) so tests can set process.env first.
 * A missing token fails at startup, not as an auth error on every tool call.
 */
import { homedir } from 'node:os';
import { join } from 'node:path';

export interface Config {
  backendUrl: string;
  token: string;
  auditLogPath: string;
}

export class MissingEnvError extends Error {
  constructor(name: string) {
    super(`Missing required environment variable: ${name}`);
    this.name = 'MissingEnvError';
  }
}

export function loadConfig(env: NodeJS.ProcessEnv = process.env): Config {
  const url = env.BACKEND_URL;
  if (!url) throw new MissingEnvError('BACKEND_URL');
  const token = env.BACKEND_TOKEN;
  if (!token || token.trim() === '') throw new MissingEnvError('BACKEND_TOKEN');
  return {
    backendUrl: url.replace(/\/+$/, ''),
    token,
    auditLogPath: env.MCP_AUDIT_LOG || join(homedir(), '.local', 'state', 'mcp-backend-wrapper', 'audit.jsonl'),
  };
}

export function authHeaders(cfg: Config): Record<string, string> {
  return {
    Authorization: `Bearer ${cfg.token}`,
    'Content-Type': 'application/json',
    Accept: 'application/json',
  };
}
