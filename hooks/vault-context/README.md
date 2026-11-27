# vault-context

At session start, gives Claude the vault note of the project you are in.

Long-lived knowledge about a project (current state, decisions, lessons) lives in
a vault, one note per repository. This hook finds the note whose frontmatter says
`repo: <this repository>` and prints it, so it is in Claude's context before you
type anything. No match on `repo:`? It falls back to a note named after the
repository folder. No note at all? It prints nothing.

```markdown
---
type: project
repo: ~/code/acme-shop
---
# acme-shop
## Current state
- ...
```

Explained step by step in chapter 1 of the guide:
[Start a session with context](https://tools.theuws.com/guide/start-a-session/).

## Install

```bash
cp vault-context.sh ~/.claude/hooks/ && chmod +x ~/.claude/hooks/vault-context.sh
export VAULT_DIR="$HOME/vault"     # in your shell profile
```

```json
{
  "hooks": {
    "SessionStart": [{ "hooks": [{ "type": "command", "command": "bash ~/.claude/hooks/vault-context.sh", "timeout": 3 }] }]
  }
}
```

| Variable | Default | |
|---|---|---|
| `VAULT_DIR` | `~/vault` | vault root |
| `VAULT_PROJECTS` | `$VAULT_DIR/projects` | folder with project notes |
| `VAULT_CONTEXT_MAX` | `80` | max lines printed |

Try it with the demo vault: `export VAULT_DIR="$PWD/examples/demo-vault"`.

Plain bash and grep, no network; it never fails the session.

## Test

```bash
bash test_vault_context.sh   # 7 cases
```

## Make this better

How do you give Claude project context at the start? Tell us in the
[discussions](https://github.com/RichardTheuws/ai-toolkit/discussions).
