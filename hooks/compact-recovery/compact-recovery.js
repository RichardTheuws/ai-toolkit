#!/usr/bin/env node
/**
 * compact-recovery.js: after Claude Code compacts the conversation, tell Claude
 * where it was: branch, uncommitted files, recent commits.
 *
 * Wire it to SessionStart with matcher "compact". That event fires right after
 * compaction, and its additionalContext is added to the new context.
 * (A PreCompact hook cannot do this: its output only steers the summary.)
 *
 * Never fails the session; outside a git repo it prints a short note only.
 */
const { execFileSync } = require("child_process");
const fs = require("fs");

function git(cwd, args) {
  try {
    return execFileSync("git", ["-C", cwd, ...args], { encoding: "utf8", timeout: 3000, stdio: ["ignore", "pipe", "ignore"] }).trim();
  } catch {
    return "";
  }
}

let input = {};
try {
  input = JSON.parse(fs.readFileSync(0, "utf8") || "{}");
} catch {}
const cwd = input.cwd || process.cwd();

const lines = [`[After compaction] Working directory: ${cwd}`];
const branch = git(cwd, ["branch", "--show-current"]);
if (branch || git(cwd, ["rev-parse", "--git-dir"])) {
  const dirty = git(cwd, ["status", "--porcelain"]);
  const count = dirty ? dirty.split("\n").length : 0;
  const commits = git(cwd, ["log", "--oneline", "-5"]);
  lines.push(`Branch: ${branch || "(detached)"}`);
  lines.push(count ? `${count} uncommitted file(s); run git status before continuing.` : "Working tree clean.");
  if (commits) lines.push(`Recent commits:\n${commits}`);
}
lines.push("Re-read MEMORY.md and the task list before you continue.");

process.stdout.write(
  JSON.stringify({
    hookSpecificOutput: { hookEventName: "SessionStart", additionalContext: lines.join("\n") },
  })
);
