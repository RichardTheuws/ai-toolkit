import { describe, expect, it } from 'vitest';
import { allTools, fromBackend, runTool, toBackend, TasksUpdateInput, type ToolContext } from '../src/tools.js';
import { inputShapeOf } from '../src/server.js';
import { loadConfig, MissingEnvError } from '../src/config.js';

const tool = (name: string) => allTools.find((t) => t.name === name)!;

function ctxWith(response: unknown, status = 200) {
  const calls: { url: string; init: RequestInit }[] = [];
  const lines: string[] = [];
  const ctx: ToolContext = {
    config: () => ({ backendUrl: 'https://api.example.com', token: 't', auditLogPath: '/dev/null' }),
    fetch: (async (url: string, init: RequestInit) => {
      calls.push({ url, init });
      return new Response(JSON.stringify(response), { status });
    }) as unknown as typeof fetch,
    auditWriter: (_p, line) => lines.push(line),
  };
  return { ctx, calls, lines };
}

describe('priority mapping', () => {
  it('maps both ways', () => {
    expect(toBackend('high')).toBe('week');
    expect(fromBackend('week')).toBe('high');
    expect(toBackend('urgent')).toBe('urgent');
  });

  it('sends week and returns high', async () => {
    const { ctx, calls } = ctxWith([{ id: '1', priority: 'week' }]);
    const out = await runTool(tool('tasks_list'), { priority: 'high' }, ctx);
    expect(calls[0].url).toContain('priority=week');
    expect(out).toEqual([{ id: '1', priority: 'high' }]);
  });
});

describe('registration', () => {
  it('every tool has an input shape, also the refined one', () => {
    for (const t of allTools) expect(inputShapeOf(t.inputSchema), t.name).toBeDefined();
    expect(Object.keys(inputShapeOf(TasksUpdateInput)!)).toContain('id');
  });
});

describe('validation and audit', () => {
  it('rejects unknown fields', async () => {
    const { ctx } = ctxWith({});
    await expect(runTool(tool('tasks_create'), { title: 'x', color: 'red' }, ctx)).rejects.toThrow();
  });

  it('rejects an update without changes', async () => {
    const { ctx } = ctxWith({});
    await expect(runTool(tool('tasks_update'), { id: '1' }, ctx)).rejects.toThrow(/at least one field/);
  });

  it('audits success and failure, and re-throws errors', async () => {
    const ok = ctxWith({ id: '1', status: 'done' });
    await runTool(tool('tasks_update'), { id: '1', status: 'done' }, ok.ctx);
    expect(JSON.parse(ok.lines[0])).toMatchObject({ tool: 'tasks_update', action: 'write', success: true });
    expect(ok.calls[0].init.method).toBe('PATCH');

    const bad = ctxWith({ error: 'nope' }, 500);
    await expect(runTool(tool('tasks_list'), {}, bad.ctx)).rejects.toThrow(/HTTP 500/);
    expect(JSON.parse(bad.lines[0])).toMatchObject({ success: false });
  });
});

describe('config', () => {
  it('fails fast without a token', () => {
    expect(() => loadConfig({ BACKEND_URL: 'https://x.example.com' })).toThrow(MissingEnvError);
  });
  it('strips trailing slashes', () => {
    expect(loadConfig({ BACKEND_URL: 'https://x.example.com//', BACKEND_TOKEN: 't' }).backendUrl).toBe('https://x.example.com');
  });
});
