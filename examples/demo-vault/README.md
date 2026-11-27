# demo-vault

A tiny example vault for trying the tools in this repo. Everything in it is made up.

```bash
export VAULT_DIR="$PWD/examples/demo-vault"
```

- `projects/acme-shop.md`: a project note with `repo:` frontmatter (read by `hooks/vault-context`)
- `decisions/`, `learnings/`: what `/decision` and `/learning` write
- `dev-actions/acme-shop/`: work filed for the project (picked up by `/session-start`)
- `overviews/this-week.md`: an example of a generated overview note (rebuilt by a script, never edited by hand)
- `daily/`, `inbox/`: a daily note and a quick capture

Open the folder in Obsidian to see the links, or just read the markdown.
