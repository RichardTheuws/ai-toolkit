# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project uses [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-11-27

### Added
- `commands/session-start.md`: a lean `/session-start` (git, last session, memory audit, vault note, open dev actions, one banner).
- `hooks/vault-context`: gives Claude the vault note of the current repository at session start (7 tests).
- `examples/demo-vault`: a small made-up vault to try the hooks and commands.
- The READMEs point to the guide on tools.theuws.com.

## [0.1.1] - 2026-11-27

### Fixed
- CI: run the sound-cues tests by file name; Node 22 does not accept a folder for `--test`.

## [0.1.0] - 2026-11-27

### Added
- Hooks: bash-guard, session-tracker, compact-recovery, sound-cues.
- Commands: /decision, /learning.
- Scripts: memory-audit, leak-gate.
- Skill: li-check (derived from Jake Schincariol's linkedin-agent-skill, MIT).
- Template: mcp-backend-wrapper.
- Playbooks in English and Dutch: working agreements, memory hygiene, Obsidian as shared memory,
  personal assistant, integration standard, running on a Mac mini, one app for the whole house.
