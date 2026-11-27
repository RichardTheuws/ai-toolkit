#!/usr/bin/env node
// sound-cues CLI: list, switch, add and test sound packs.
// Usage: node sound-cues-cli.js <command> [args]   (run without args for help)

'use strict';

const fs = require('fs');
const path = require('path');
const core = require('./sound-cues.js');

const P = core.paths();
const SOUND_NAMES = ['ready', 'acknowledge', 'work', 'command', 'error', 'done', 'alert', 'idle'];
const EVENTS = ['SessionStart', 'UserPromptSubmit', 'PostToolUse', 'PostToolUseFailure', 'Stop', 'Notification'];

function fail(msg) {
  console.error(msg);
  process.exit(1);
}

function readUserConfig() {
  try { return JSON.parse(fs.readFileSync(P.config, 'utf8')); } catch { return {}; }
}

function saveUserConfig(patch) {
  const next = { ...readUserConfig(), ...patch };
  fs.writeFileSync(P.config, JSON.stringify(next, null, 2) + '\n');
}

function readSessions() {
  try { return JSON.parse(fs.readFileSync(P.sessions, 'utf8')); } catch { return {}; }
}

function writeSessions(s) {
  fs.writeFileSync(P.sessions, JSON.stringify(s, null, 2) + '\n');
}

function installedPacks() {
  let entries = [];
  try { entries = fs.readdirSync(P.packs, { withFileTypes: true }); } catch { return []; }
  return entries
    .filter((e) => e.isDirectory() && core.loadPack(e.name))
    .map((e) => e.name)
    .sort();
}

function requirePack(name) {
  if (!name) fail('Give a pack name. See: list');
  if (!core.isValidPackName(name)) fail(`Invalid pack name "${name}". Use letters, digits, dot, dash, underscore.`);
  const pack = core.loadPack(name);
  if (!pack) fail(`Pack "${name}" not found (or its pack.json is not valid JSON). See: list`);
  return pack;
}

const commands = {
  status() {
    const cfg = core.loadConfig();
    const sp = core.sessionPack();
    console.log(`enabled:      ${cfg.enabled ? 'yes' : 'no'}`);
    console.log(`global pack:  ${cfg.activePack}`);
    if (process.env.SOUND_CUES_PACK) console.log(`env pack:     ${process.env.SOUND_CUES_PACK} (SOUND_CUES_PACK)`);
    if (sp) console.log(`this tab:     ${sp}`);
    console.log(`volume:       ${cfg.volume}`);
    console.log(`config:       ${P.config}${fs.existsSync(P.config) ? '' : ' (not created yet, using defaults)'}`);
    const off = Object.entries(cfg.eventOverrides).filter(([, v]) => v === false).map(([k]) => k);
    console.log(`muted events: ${off.length ? off.join(', ') : 'none'}`);
  },

  list() {
    const cfg = core.loadConfig();
    const names = installedPacks();
    if (!names.length) { console.log(`No packs in ${P.packs}`); return; }
    for (const name of names) {
      const pack = core.loadPack(name);
      const sounds = pack.sounds || {};
      const files = Object.values(sounds).reduce((n, v) => n + (Array.isArray(v) ? v.length : 1), 0);
      const mark = name === cfg.activePack ? '  (active)' : '';
      console.log(`${name}${mark}`);
      console.log(`  ${pack.name || name}: ${Object.keys(sounds).length} sounds, ${files} files`);
      if (pack.description) console.log(`  ${pack.description}`);
    }
  },

  use(name) {
    const pack = requirePack(name);
    saveUserConfig({ activePack: name });
    console.log(`Active pack: ${pack.name || name}`);
  },

  session(name) {
    const key = core.sessionKey();
    if (!key) {
      fail('This terminal exposes no session id. Use instead: export SOUND_CUES_PACK=<pack>');
    }
    const sessions = readSessions();
    if (!name) {
      console.log(sessions[key] ? `This tab: ${sessions[key].pack}` : 'No pack set for this tab.');
      return;
    }
    const pack = requirePack(name);
    const now = Date.now();
    for (const [k, v] of Object.entries(sessions)) {
      if (!v || !v.ts || now - v.ts > core.SESSION_TTL_MS) delete sessions[k];
    }
    sessions[key] = { pack: name, ts: now };
    writeSessions(sessions);
    console.log(`This tab now uses: ${pack.name || name} (for 24 hours)`);
  },

  'session-clear'() {
    const key = core.sessionKey();
    const sessions = readSessions();
    if (key && sessions[key]) {
      delete sessions[key];
      writeSessions(sessions);
      console.log('Tab override removed.');
    } else {
      console.log('No tab override set.');
    }
  },

  add(source, name) {
    if (!source) fail('Usage: add <folder-with-pack.json> [name]');
    const src = path.resolve(source);
    let pack;
    try { pack = JSON.parse(fs.readFileSync(path.join(src, 'pack.json'), 'utf8')); } catch {
      fail(`No valid pack.json in ${src}. See packs/README.md for the format.`);
    }
    const target = name || path.basename(src);
    if (!core.isValidPackName(target)) fail(`Invalid pack name "${target}". Pass a name as second argument.`);
    const dest = path.join(P.packs, target);
    if (fs.existsSync(dest)) fail(`Pack "${target}" already exists. Remove it first or pick another name.`);
    fs.cpSync(src, dest, { recursive: true });
    const missing = [];
    for (const key of Object.keys(pack.sounds || {})) {
      for (const f of core.soundFiles(key, target)) if (!fs.existsSync(f)) missing.push(f);
    }
    console.log(`Added pack "${target}". Switch with: use ${target}`);
    if (missing.length) console.log(`Warning, files not found:\n  ${missing.join('\n  ')}`);
  },

  remove(name) {
    requirePack(name);
    if (name === 'system-default') fail('system-default stays; it is the fallback.');
    if (core.loadConfig().activePack === name) saveUserConfig({ activePack: 'system-default' });
    fs.rmSync(path.join(P.packs, name), { recursive: true, force: true });
    console.log(`Removed pack "${name}".`);
  },

  async test(soundName) {
    const cfg = core.loadConfig();
    const name = core.sessionPack() || process.env.SOUND_CUES_PACK || cfg.activePack;
    const pack = requirePack(name);
    const list = soundName ? [soundName] : SOUND_NAMES;
    console.log(`Testing ${pack.name || name} at volume ${cfg.volume}`);
    for (const s of list) {
      const files = core.soundFiles(s, name);
      if (!files.length) { console.log(`  ${s}: not mapped (silent)`); continue; }
      const file = core.resolveSoundPath(s, name);
      if (!file) { console.log(`  ${s}: file not found: ${files[0]}`); continue; }
      const variants = files.length > 1 ? ` (1 of ${files.length})` : '';
      process.stdout.write(`  ${s}${variants}: ${path.basename(file)} ... `);
      const ok = await core.playSound(file, cfg.volume, { wait: true });
      console.log(ok ? 'ok' : 'could not play (no player found?)');
    }
  },

  volume(level) {
    const v = parseFloat(level);
    if (!Number.isFinite(v) || v < 0 || v > 1) fail('Usage: volume <0.0-1.0>');
    saveUserConfig({ volume: v });
    console.log(`Volume: ${v}`);
  },

  on() { saveUserConfig({ enabled: true }); console.log('Sounds on.'); },
  off() { saveUserConfig({ enabled: false }); console.log('Sounds off.'); },

  event(name, state) {
    if (!EVENTS.includes(name) || !['on', 'off'].includes(state)) {
      fail(`Usage: event <${EVENTS.join('|')}> on|off`);
    }
    const overrides = { ...(readUserConfig().eventOverrides || {}), [name]: state === 'on' };
    saveUserConfig({ eventOverrides: overrides });
    console.log(`${name}: ${state}`);
  },

  init() {
    if (fs.existsSync(P.config)) { console.log(`Config already exists: ${P.config}`); return; }
    fs.writeFileSync(P.config, JSON.stringify(core.DEFAULT_CONFIG, null, 2) + '\n');
    console.log(`Created ${P.config}`);
  },

  help() {
    console.log(`sound-cues: sounds for Claude Code events

Usage: node sound-cues-cli.js <command> [args]

  status                 Show settings and which pack plays
  list                   List installed packs
  use <pack>             Switch the global pack
  session [pack]         Use a pack in this terminal tab only (or show it)
  session-clear          Drop the tab override
  add <folder> [name]    Copy a folder with pack.json into packs/
  remove <pack>          Delete an installed pack
  test [sound]           Play every sound of the current pack, or one
  volume <0.0-1.0>       Set volume
  on | off               Turn all sounds on or off
  event <Event> on|off   Mute or unmute one hook event
  init                   Write config.json with the defaults

Sounds: ${SOUND_NAMES.join(', ')}`);
  },
};

const [cmd, ...args] = process.argv.slice(2);
if (!cmd || !commands[cmd]) {
  commands.help();
  process.exit(cmd ? 1 : 0);
}
Promise.resolve()
  .then(() => commands[cmd](...args))
  .catch((err) => fail(`Error: ${err.message}`));
