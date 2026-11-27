#!/usr/bin/env node
/**
 * session-tracker.js: one line per Claude Code session in a JSONL log,
 * with project, start, end and duration.
 *
 *   SessionStart -> node session-tracker.js start   (remembers the start time per session_id)
 *   SessionEnd   -> node session-tracker.js end     (appends the entry, rotates the log)
 *
 * Why SessionEnd and not Stop: Stop fires after every reply, so you get one line
 * per turn instead of one per session.
 *
 * Log: ~/.claude/session-log.jsonl (override with CLAUDE_SESSION_LOG).
 * Keeps the last 500 sessions. Never fails the session: all errors are swallowed.
 */
const fs = require("fs");
const os = require("os");
const path = require("path");

const HOME = process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), ".claude");
const LOG_FILE = process.env.CLAUDE_SESSION_LOG || path.join(HOME, "session-log.jsonl");
const START_DIR = path.join(HOME, ".session-starts");
const MAX_ENTRIES = 500;

function main() {
  const event = process.argv[2] || "end";
  let input = {};
  try {
    input = JSON.parse(fs.readFileSync(0, "utf8") || "{}");
  } catch {}
  const id = String(input.session_id || "unknown").replace(/[^A-Za-z0-9_-]/g, "");
  const startFile = path.join(START_DIR, id);
  const cwd = input.cwd || process.cwd();

  if (event === "start") {
    // A resumed or compacted session keeps its original start time.
    if (input.source && input.source !== "startup" && fs.existsSync(startFile)) return;
    fs.mkdirSync(START_DIR, { recursive: true });
    fs.writeFileSync(startFile, new Date().toISOString());
    return;
  }

  let started = null;
  try {
    started = fs.readFileSync(startFile, "utf8").trim();
    fs.unlinkSync(startFile);
  } catch {}
  const end = new Date();
  const entry = {
    project: path.basename(cwd),
    cwd,
    session_id: input.session_id || null,
    started,
    ended: end.toISOString(),
    duration_min: started ? Math.round((end - new Date(started)) / 60000) : null,
    reason: input.reason || null,
  };
  fs.mkdirSync(path.dirname(LOG_FILE), { recursive: true });
  fs.appendFileSync(LOG_FILE, JSON.stringify(entry) + "\n");

  const lines = fs.readFileSync(LOG_FILE, "utf8").trim().split("\n");
  if (lines.length > MAX_ENTRIES * 1.5) {
    fs.writeFileSync(LOG_FILE, lines.slice(-MAX_ENTRIES).join("\n") + "\n");
  }
}

try {
  main();
} catch {}
