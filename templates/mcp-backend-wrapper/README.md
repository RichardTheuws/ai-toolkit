# mcp-backend-wrapper

A small template for putting your own app's API behind MCP, so Claude Code can
use it as tools. We built the original for our own bookkeeping backend, so that
"what's on my list this week?" and "mark that one done" work from any Claude
Code session. This is the same structure with a generic task API.

What you get:

- three example tools (`tasks_list`, `tasks_create`, `tasks_update`) with zod schemas
- bearer-token auth from environment variables, failing fast when the token is missing
- an append-only JSONL audit log: one line per call, success or failure
- tests with a fake `fetch`, so you can test without a running backend

## Two mistakes we made, so you don't have to

**A refined schema registers without parameters.** The MCP SDK wants the raw
`.shape` of a zod object. Add `.refine()` and the schema becomes a `ZodEffects`;
an `instanceof ZodObject` check then fails quietly and the tool is registered
with no parameters. The model sees an empty parameter list and every argument is
dropped. `inputShapeOf()` in `src/server.ts` unwraps it, and the server refuses to
start if any tool ends up without a shape.

**Your backend's words are not the model's words.** Our backend stored priority
as `urgent | week | later`; the model kept sending `high`. On reads that silently
matched nothing, on writes it hit a database enum error. The fix is one mapping,
in one place, both directions (`toBackend` / `fromBackend` in `src/tools.ts`).

## Use it

```bash
npm install
npm test
npm run build
claude mcp add my-backend --scope user \
  -e BACKEND_URL=https://tasks.example.com -e BACKEND_TOKEN=your-token \
  -- node "$PWD/dist/server.js"
```

Then replace the tools in `src/tools.ts` with your own endpoints. Keep each tool
small, write its description for the model, and prefer reversible operations
(we left out delete on purpose).

Audit log: `$MCP_AUDIT_LOG`, default `~/.local/state/mcp-backend-wrapper/audit.jsonl`.

Node 20+.

## Make this better

What did you put behind MCP, and what surprised you? Tell us in the
[discussions](https://github.com/RichardTheuws/ai-toolkit/discussions).
