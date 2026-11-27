#!/usr/bin/env node
/**
 * stdio MCP server exposing the tools in tools.ts.
 *
 *   npm install && npm run build
 *   claude mcp add my-backend --scope user \
 *     -e BACKEND_URL=https://tasks.example.com -e BACKEND_TOKEN=... \
 *     -- node /path/to/mcp-backend-wrapper/dist/server.js
 */
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z, ZodEffects, ZodObject } from 'zod';
import { loadConfig, MissingEnvError } from './config.js';
import { allTools, createContext, runTool, type ToolContext } from './tools.js';

/**
 * The MCP SDK wants the raw `.shape` of an object schema. A schema with
 * `.refine()` is a ZodEffects, not a ZodObject, so a plain `instanceof ZodObject`
 * check falls through and the tool gets registered WITHOUT parameters: the model
 * sees an empty parameter list and every argument it sends is dropped. Unwrap
 * the effects to get the shape; the full schema still validates the input.
 */
export function inputShapeOf(schema: z.ZodTypeAny): Record<string, z.ZodTypeAny> | undefined {
  let s: z.ZodTypeAny = schema;
  while (s instanceof ZodEffects) s = s.innerType() as z.ZodTypeAny;
  return s instanceof ZodObject ? (s.shape as Record<string, z.ZodTypeAny>) : undefined;
}

export function buildServer(ctx: ToolContext = createContext()): McpServer {
  const server = new McpServer({ name: 'mcp-backend-wrapper', version: '0.1.0' });
  for (const tool of allTools) {
    const shape = inputShapeOf(tool.inputSchema);
    if (!shape) throw new Error(`${tool.name}: no input shape; it would be registered without parameters.`);
    server.registerTool(tool.name, { description: tool.description, inputSchema: shape }, async (args: unknown) => {
      const result = await runTool(tool, args, ctx);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    });
  }
  return server;
}

async function main(): Promise<void> {
  try {
    loadConfig();
  } catch (err) {
    if (err instanceof MissingEnvError) {
      process.stderr.write(`[mcp-backend-wrapper] ${err.message}\n`);
      process.exit(1);
    }
    throw err;
  }
  await buildServer().connect(new StdioServerTransport());
  process.stderr.write('[mcp-backend-wrapper] connected over stdio\n');
}

if (process.argv[1] && import.meta.url === new URL(`file://${process.argv[1]}`).href) {
  main().catch((err) => {
    process.stderr.write(`[mcp-backend-wrapper] fatal: ${(err as Error).stack ?? err}\n`);
    process.exit(1);
  });
}
