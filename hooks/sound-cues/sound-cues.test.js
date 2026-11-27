// Run: node --test   (from this folder)
// No audio is played: every test runs with SOUND_CUES_DRY_RUN=1 and a temp SOUND_CUES_HOME.

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

process.env.SOUND_CUES_DRY_RUN = '1';
const core = require('./sound-cues.js');
const HOOK = path.join(__dirname, 'sound-cues.js');

function tempHome({ config, packs = {} } = {}) {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'sound-cues-'));
  fs.mkdirSync(path.join(home, 'packs'));
  if (config) fs.writeFileSync(path.join(home, 'config.json'), JSON.stringify(config));
  for (const [name, { pack, files = [] }] of Object.entries(packs)) {
    const dir = path.join(home, 'packs', name);
    fs.mkdirSync(dir);
    fs.writeFileSync(path.join(dir, 'pack.json'), typeof pack === 'string' ? pack : JSON.stringify(pack));
    for (const f of files) fs.writeFileSync(path.join(dir, f), 'x');
  }
  return home;
}

function runHook(input, env = {}) {
  return spawnSync(process.execPath, [HOOK], {
    input,
    encoding: 'utf8',
    timeout: 5000,
    env: { ...process.env, SOUND_CUES_DRY_RUN: '1', ...env },
  });
}

const NO_COOLDOWN = { cooldowns: { global: 0, PostToolUse: 0, PostToolUseFailure: 0, Notification: 0 } };

test('event to sound mapping', () => {
  const cases = [
    ['SessionStart', {}, 'ready'],
    ['UserPromptSubmit', {}, 'acknowledge'],
    ['PostToolUse', { tool_name: 'Edit' }, 'work'],
    ['PostToolUse', { tool_name: 'Write' }, 'work'],
    ['PostToolUse', { tool_name: 'MultiEdit' }, 'work'],
    ['PostToolUse', { tool_name: 'NotebookEdit' }, 'work'],
    ['PostToolUse', { tool_name: 'Bash' }, 'command'],
    ['PostToolUse', { tool_name: 'Read' }, null],
    ['PostToolUseFailure', { tool_name: 'Bash' }, 'error'],
    ['Stop', {}, 'done'],
    ['Notification', { notification_type: 'permission_prompt' }, 'alert'],
    ['Notification', { notification_type: 'idle_prompt' }, 'idle'],
    ['Notification', { notification_type: 'something_else' }, null],
    ['PreCompact', {}, null],
    [undefined, {}, null],
  ];
  for (const [event, data, want] of cases) {
    assert.equal(core.mapEventToSound(event, data), want, `${event} ${JSON.stringify(data)}`);
  }
});

test('resolves relative files and picks only existing variants', () => {
  const home = tempHome({
    packs: { mine: { pack: { sounds: { done: ['a.wav', 'gone.wav'], ready: 'r.wav' } }, files: ['a.wav', 'r.wav'] } },
  });
  assert.equal(core.resolveSoundPath('ready', 'mine', home), path.join(home, 'packs', 'mine', 'r.wav'));
  for (let i = 0; i < 20; i++) {
    assert.equal(core.resolveSoundPath('done', 'mine', home), path.join(home, 'packs', 'mine', 'a.wav'));
  }
});

test('missing file, unmapped sound, unknown or broken pack return null without throwing', () => {
  const home = tempHome({
    packs: {
      empty: { pack: { sounds: { done: 'missing.wav' } } },
      broken: { pack: '{not json' },
    },
  });
  assert.equal(core.resolveSoundPath('done', 'empty', home), null);
  assert.equal(core.resolveSoundPath('ready', 'empty', home), null);
  assert.equal(core.resolveSoundPath('done', 'does-not-exist', home), null);
  assert.equal(core.resolveSoundPath('done', 'broken', home), null);
  assert.equal(core.resolveSoundPath('done', '../escape', home), null);
});

test('chooseSound honours enabled, eventOverrides and env pack', () => {
  const packs = {
    a: { pack: { sounds: { done: 'a.wav' } }, files: ['a.wav'] },
    b: { pack: { sounds: { done: 'b.wav' } }, files: ['b.wav'] },
  };
  const env = {};
  let home = tempHome({ config: { ...NO_COOLDOWN, activePack: 'a' }, packs });
  assert.equal(core.chooseSound({ hook_event_name: 'Stop' }, { home, env }).pack, 'a');
  assert.equal(core.chooseSound({ hook_event_name: 'Stop' }, { home, env: { SOUND_CUES_PACK: 'b' } }).pack, 'b');

  home = tempHome({ config: { ...NO_COOLDOWN, activePack: 'a', enabled: false }, packs });
  assert.equal(core.chooseSound({ hook_event_name: 'Stop' }, { home, env }), null);

  home = tempHome({ config: { ...NO_COOLDOWN, activePack: 'a', eventOverrides: { Stop: false } }, packs });
  assert.equal(core.chooseSound({ hook_event_name: 'Stop' }, { home, env }), null);
});

test('per-terminal session pack wins over config and expires', () => {
  const packs = {
    a: { pack: { sounds: { done: 'a.wav' } }, files: ['a.wav'] },
    b: { pack: { sounds: { done: 'b.wav' } }, files: ['b.wav'] },
  };
  const home = tempHome({ config: { ...NO_COOLDOWN, activePack: 'a' }, packs });
  const env = { TERM_SESSION_ID: 'tab-1' };
  fs.writeFileSync(path.join(home, '.sessions.json'), JSON.stringify({ 'tab-1': { pack: 'b', ts: Date.now() } }));
  assert.equal(core.chooseSound({ hook_event_name: 'Stop' }, { home, env }).pack, 'b');
  assert.equal(core.chooseSound({ hook_event_name: 'Stop' }, { home, env: { TERM_SESSION_ID: 'tab-2' } }).pack, 'a');

  const old = Date.now() - core.SESSION_TTL_MS - 1000;
  fs.writeFileSync(path.join(home, '.sessions.json'), JSON.stringify({ 'tab-1': { pack: 'b', ts: old } }));
  assert.equal(core.chooseSound({ hook_event_name: 'Stop' }, { home, env }).pack, 'a');
});

test('cooldown blocks a repeat within the window', () => {
  const home = tempHome();
  const cfg = core.loadConfig(home);
  assert.equal(core.checkCooldown('PostToolUse', cfg, home, 1_000_000), true);
  assert.equal(core.checkCooldown('PostToolUse', cfg, home, 1_000_500), false);
  assert.equal(core.checkCooldown('PostToolUse', cfg, home, 1_003_000), true);
});

test('player selection per platform', () => {
  assert.deepEqual(core.playerFor('/x.aiff', 0.5, 'darwin'), ['afplay', ['--volume', '0.5', '/x.aiff']]);
  assert.equal(core.playerFor('/x.wav', 1, 'linux')[0], 'aplay');
  assert.deepEqual(core.playerFor('/x.oga', 1, 'linux'), ['paplay', ['--volume=65536', '/x.oga']]);
  assert.equal(core.playerFor('/x.wav', 0.5, 'win32'), null);
});

test('hook process always exits 0 and stays silent on stdout', () => {
  const home = tempHome({
    config: NO_COOLDOWN,
    packs: { 'system-default': { pack: { sounds: { done: 'd.wav' } }, files: ['d.wav'] } },
  });
  const env = { SOUND_CUES_HOME: home, SOUND_CUES_PACK: '' };

  const ok = runHook('{"hook_event_name":"Stop"}', env);
  assert.equal(ok.status, 0);
  assert.equal(ok.stdout, '');
  assert.match(ok.stderr, /would play .*d\.wav/);

  for (const input of ['', 'not json', '{}', '{"hook_event_name":"Nope"}', '[1,2]', 'null']) {
    const r = runHook(input, env);
    assert.equal(r.status, 0, `input ${JSON.stringify(input)}`);
    assert.equal(r.stdout, '');
  }

  const unknown = runHook('{"hook_event_name":"Stop"}', { ...env, SOUND_CUES_PACK: 'nope' });
  assert.equal(unknown.status, 0);
  assert.equal(unknown.stderr, '');

  const noHome = runHook('{"hook_event_name":"Stop"}', { SOUND_CUES_HOME: path.join(home, 'missing') });
  assert.equal(noHome.status, 0);
});

test('bundled system-default pack is valid and complete', () => {
  const pack = core.loadPack('system-default', __dirname);
  assert.ok(pack);
  for (const s of ['ready', 'acknowledge', 'work', 'command', 'error', 'done', 'alert', 'idle']) {
    assert.match(pack.sounds[s], /^\/System\/Library\/Sounds\/\w+\.aiff$/);
  }
});
