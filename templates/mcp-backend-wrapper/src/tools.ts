/**
 * The tools Claude sees. This example wraps a small task API:
 *
 *   tasks_list    -> GET   /api/tasks?status=&priority=&limit=
 *   tasks_create  -> POST  /api/tasks
 *   tasks_update  -> PATCH /api/tasks/:id
 *
 * Replace these with your own endpoints. Keep the shape: a zod schema, a short
 * description written for the model, and a handler that audits every call.
 */
import { z } from 'zod';
import { authHeaders, loadConfig, type Config } from './config.js';
import { audit, type Writer } from './audit.js';

/* ---------- Vocabulary mapping --------------------------------------------
 * Your backend's words are not always the best words for the model. Here the
 * backend stores priority as `urgent | week | later`, but `high` is what a
 * model (and a person) naturally says. Map in ONE place, in both directions.
 * Without this, `high` silently matched nothing on reads and hit a database
 * enum error on writes.
 */
export type ToolPriority = 'urgent' | 'high' | 'later';
export type BackendPriority = 'urgent' | 'week' | 'later';
export const toBackend = (p: ToolPriority): BackendPriority => (p === 'high' ? 'week' : p);
export const fromBackend = (p: BackendPriority): ToolPriority => (p === 'week' ? 'high' : p);

function translateOut(data: unknown): unknown {
  const fix = (t: unknown) =>
    t && typeof t === 'object' && (t as { priority?: string }).priority === 'week'
      ? { ...(t as object), priority: 'high' }
      : t;
  if (Array.isArray(data)) return data.map(fix);
  if (data && typeof data === 'object' && Array.isArray((data as { tasks?: unknown[] }).tasks)) {
    const d = data as { tasks: unknown[] };
    return { ...d, tasks: d.tasks.map(fix) };
  }
  return fix(data);
}

/* ---------- Input schemas ------------------------------------------------- */

export const TasksListInput = z
  .object({
    status: z.enum(['open', 'done', 'all']).optional(),
    priority: z.enum(['urgent', 'high', 'later', 'all']).optional(),
    limit: z.number().int().positive().max(200).optional(),
  })
  .strict();

export const TasksCreateInput = z
  .object({
    title: z.string().min(1),
    description: z.string().optional(),
    priority: z.enum(['urgent', 'high', 'later']).optional(),
    dueDate: z.string().datetime({ offset: true }).optional(),
  })
  .strict();

/** One task per call, no delete: everything this tool does can be undone. */
export const TasksUpdateInput = z
  .object({
    id: z.string().min(1),
    status: z.enum(['open', 'done']).optional(),
    title: z.string().min(1).optional(),
    priority: z.enum(['urgent', 'high', 'later']).optional(),
  })
  .strict()
  .refine((v) => Object.keys(v).length > 1, { message: 'Give at least one field to change besides id.' });

/* ---------- Context + HTTP ------------------------------------------------ */

export interface ToolContext {
  config: () => Config;
  fetch: typeof fetch;
  auditWriter?: Writer;
}

export function createContext(): ToolContext {
  let cfg: Config | undefined;
  return { config: () => (cfg ??= loadConfig()), fetch: globalThis.fetch };
}

async function call(ctx: ToolContext, method: string, path: string, body?: unknown): Promise<unknown> {
  const cfg = ctx.config();
  const res = await ctx.fetch(`${cfg.backendUrl}${path}`, {
    method,
    headers: authHeaders(cfg),
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`${method} ${path} -> HTTP ${res.status}: ${text.slice(0, 300)}`);
  return text ? JSON.parse(text) : null;
}

/* ---------- Tool registry ------------------------------------------------- */

export interface Tool {
  name: string;
  description: string;
  action: 'read' | 'write';
  inputSchema: z.ZodTypeAny;
  run: (args: any, ctx: ToolContext) => Promise<unknown>;
}

export const allTools: Tool[] = [
  {
    name: 'tasks_list',
    description: 'List tasks. Defaults to open tasks. Use priority "high" for this-week work.',
    action: 'read',
    inputSchema: TasksListInput,
    run: async (a: z.infer<typeof TasksListInput>, ctx) => {
      const qs = new URLSearchParams();
      qs.set('status', a.status ?? 'open');
      if (a.priority && a.priority !== 'all') qs.set('priority', toBackend(a.priority));
      if (a.limit) qs.set('limit', String(a.limit));
      return translateOut(await call(ctx, 'GET', `/api/tasks?${qs}`));
    },
  },
  {
    name: 'tasks_create',
    description: 'Create one task. Ask the user before creating more than one.',
    action: 'write',
    inputSchema: TasksCreateInput,
    run: async (a: z.infer<typeof TasksCreateInput>, ctx) =>
      translateOut(await call(ctx, 'POST', '/api/tasks', { ...a, priority: a.priority && toBackend(a.priority) })),
  },
  {
    name: 'tasks_update',
    description: 'Update one task by id, e.g. mark it done with status "done". Reversible: status "open" reopens it.',
    action: 'write',
    inputSchema: TasksUpdateInput,
    run: async (a: z.infer<typeof TasksUpdateInput>, ctx) => {
      const { id, ...rest } = a;
      const body = { ...rest, priority: rest.priority && toBackend(rest.priority) };
      return translateOut(await call(ctx, 'PATCH', `/api/tasks/${encodeURIComponent(id)}`, body));
    },
  },
];

/** Run a tool: validate, call, audit. Errors are audited and re-thrown, never swallowed. */
export async function runTool(tool: Tool, rawArgs: unknown, ctx: ToolContext): Promise<unknown> {
  const args = tool.inputSchema.parse(rawArgs ?? {});
  const log = (success: boolean, extra: { summary?: string; error?: string }) =>
    audit(ctx.config().auditLogPath, { tool: tool.name, action: tool.action, success, ...extra }, ctx.auditWriter);
  try {
    const result = await tool.run(args, ctx);
    log(true, { summary: Array.isArray(result) ? `${result.length} item(s)` : 'ok' });
    return result;
  } catch (err) {
    log(false, { error: (err as Error).message.slice(0, 300) });
    throw err;
  }
}
