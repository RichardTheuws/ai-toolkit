#!/usr/bin/env node
// sound-cues: a Claude Code hook that plays a short sound on session events.
//
// Claude Code pipes the hook event as JSON on stdin. We map it to a sound name
// (ready, acknowledge, work, command, error, done, alert, idle), look the name up
// in the active pack, start the player detached and exit right away.
//
// This script must never slow down or break a session: every error is swallowed,
// stdin reading has a timeout, and the process always exits 0.
//
// Environment:
//   SOUND_CUES_HOME     folder with config.json and packs/ (default: this script's folder)
//   SOUND_CUES_PACK     pack to use in this terminal, overrides config.json
//   SOUND_CUES_DRY_RUN  1 = print the chosen file to stderr instead of playing it

'use strict';

const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const DEFAULT_CONFIG = {
  enabled: true,
  activePack: 'system-default',
  volume: 0.5,
  cooldowns: {
    global: 300,
    PostToolUse: 2000,
    PostToolUseFailure: 1000,
    Notification: 500,
  },
  eventOverrides: {},
};

const SESSION_TTL_MS = 24 * 60 * 60 * 1000;
const STDIN_TIMEOUT_MS = 1500;
const PACK_NAME_RE = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;

function homeDir() {
  return process.env.SOUND_CUES_HOME || __dirname;
}

function paths(home = homeDir()) {
  return {
    home,
    config: path.join(home, 'config.json'),
    packs: path.join(home, 'packs'),
    cooldown: path.join(home, '.cooldown.json'),
    sessions: path.join(home, '.sessions.json'),
  };
}

function readJson(file, fallback) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return fallback;
  }
}

function loadConfig(home) {
  const user = readJson(paths(home).config, {}) || {};
  return {
    ...DEFAULT_CONFIG,
    ...user,
    cooldowns: { ...DEFAULT_CONFIG.cooldowns, ...(user.cooldowns || {}) },
    eventOverrides: { ...(user.eventOverrides || {}) },
  };
}

// A stable id for the current terminal tab, if the terminal exposes one.
function sessionKey(env = process.env) {
  return env.ITERM_SESSION_ID || env.TERM_SESSION_ID || env.WT_SESSION ||
    env.KITTY_WINDOW_ID || env.WEZTERM_PANE || null;
}

function sessionPack(home, env = process.env) {
  const key = sessionKey(env);
  if (!key) return null;
  const entry = readJson(paths(home).sessions, {})[key];
  if (!entry || !entry.pack) return null;
  if (entry.ts && Date.now() - entry.ts > SESSION_TTL_MS) return null;
  return entry.pack;
}

function mapEventToSound(event, data = {}) {
  const tool = data.tool_name || '';
  const type = data.notification_type || '';
  switch (event) {
    case 'SessionStart': return 'ready';
    case 'UserPromptSubmit': return 'acknowledge';
    case 'PostToolUse':
      if (/^(Edit|Write|MultiEdit|NotebookEdit)$/.test(tool)) return 'work';
      if (tool === 'Bash') return 'command';
      return null;
    case 'PostToolUseFailure': return 'error';
    case 'Stop': return 'done';
    case 'Notification':
      if (type === 'permission_prompt') return 'alert';
      if (type === 'idle_prompt') return 'idle';
      return null;
    default: return null;
  }
}

function isValidPackName(name) {
  return typeof name === 'string' && PACK_NAME_RE.test(name);
}

function loadPack(packName, home) {
  if (!isValidPackName(packName)) return null;
  const pack = readJson(path.join(paths(home).packs, packName, 'pack.json'), null);
  return pack && typeof pack === 'object' ? pack : null;
}

// All candidate files for one sound name. A pack entry is a file name or a list.
function soundFiles(soundName, packName, home) {
  const pack = loadPack(packName, home);
  const value = pack && pack.sounds ? pack.sounds[soundName] : null;
  if (!value) return [];
  const list = (Array.isArray(value) ? value : [value]).filter((f) => typeof f === 'string' && f);
  const packDir = path.join(paths(home).packs, packName);
  return list.map((f) => (path.isAbsolute(f) ? f : path.join(packDir, f)));
}

// One existing file for this sound (random if the pack lists several), or null.
function resolveSoundPath(soundName, packName, home) {
  const existing = soundFiles(soundName, packName, home).filter((f) => fs.existsSync(f));
  if (existing.length === 0) return null;
  return existing[Math.floor(Math.random() * existing.length)];
}

// Rate limit per event, stored as timestamps in a small state file.
function checkCooldown(event, config, home, now = Date.now()) {
  const file = paths(home).cooldown;
  const last = readJson(file, {}) || {};
  const ms = Math.max(Number(config.cooldowns.global) || 0, Number(config.cooldowns[event]) || 0);
  if (now - (last[event] || 0) < ms) return false;
  last[event] = now;
  try { fs.writeFileSync(file, JSON.stringify(last)); } catch { /* read-only is fine */ }
  return true;
}

// Which command plays a file on this platform. Returns [cmd, args] or null.
function playerFor(filePath, volume, platform = process.platform) {
  const vol = Math.min(1, Math.max(0, Number(volume)));
  const v = Number.isFinite(vol) ? vol : 0.5;
  if (platform === 'darwin') return ['afplay', ['--volume', String(v), filePath]];
  if (platform === 'linux') {
    if (/\.wav$/i.test(filePath)) return ['aplay', ['-q', filePath]];
    return ['paplay', [`--volume=${Math.round(v * 65536)}`, filePath]];
  }
  return null;
}

function playSound(filePath, volume, { wait = false } = {}) {
  return new Promise((resolve) => {
    if (process.env.SOUND_CUES_DRY_RUN === '1') {
      process.stderr.write(`[sound-cues] would play ${filePath}\n`);
      resolve(true);
      return;
    }
    const player = playerFor(filePath, volume);
    if (!player) { resolve(false); return; }
    try {
      const child = spawn(player[0], player[1], { detached: !wait, stdio: 'ignore' });
      child.on('error', () => resolve(false));
      if (wait) {
        child.on('close', (code) => resolve(code === 0));
      } else {
        child.unref();
        resolve(true);
      }
    } catch {
      resolve(false);
    }
  });
}

function readStdin(timeoutMs = STDIN_TIMEOUT_MS) {
  return new Promise((resolve) => {
    const chunks = [];
    const done = () => resolve(Buffer.concat(chunks).toString().trim());
    const timer = setTimeout(done, timeoutMs);
    process.stdin.on('data', (c) => chunks.push(c));
    process.stdin.on('end', () => { clearTimeout(timer); done(); });
    process.stdin.on('error', () => { clearTimeout(timer); done(); });
  });
}

// The whole hook decision, without side effects beyond the cooldown file.
function chooseSound(data, { home = homeDir(), env = process.env } = {}) {
  const event = data && data.hook_event_name;
  if (!event) return null;
  const config = loadConfig(home);
  if (!config.enabled) return null;
  if (config.eventOverrides[event] === false) return null;
  const soundName = mapEventToSound(event, data);
  if (!soundName) return null;
  if (!checkCooldown(event, config, home)) return null;
  const pack = sessionPack(home, env) || env.SOUND_CUES_PACK || config.activePack || 'system-default';
  const file = resolveSoundPath(soundName, pack, home);
  return file ? { file, volume: config.volume, soundName, pack } : null;
}

async function main() {
  try {
    const input = await readStdin();
    if (input) {
      const choice = chooseSound(JSON.parse(input));
      if (choice) await playSound(choice.file, choice.volume);
    }
  } catch {
    // Never block or fail Claude Code.
  }
  process.exit(0);
}

module.exports = {
  DEFAULT_CONFIG,
  paths,
  loadConfig,
  loadPack,
  isValidPackName,
  sessionKey,
  sessionPack,
  mapEventToSound,
  soundFiles,
  resolveSoundPath,
  checkCooldown,
  playerFor,
  playSound,
  chooseSound,
  SESSION_TTL_MS,
};

if (require.main === module) main();
