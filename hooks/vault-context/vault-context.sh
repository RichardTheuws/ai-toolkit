#!/usr/bin/env bash
# vault-context.sh: at session start, give Claude the vault note of this project.
#
# Finds the note in $VAULT_DIR/projects/ whose frontmatter says `repo: <this repo>`
# (or whose file name equals the repo folder name) and prints it, capped, so
# Claude Code adds it to the session context. SessionStart hooks may print plain
# text; it lands in the context.
#
# Never fails the session and stays fast: plain bash + grep, no network.
#
#   VAULT_DIR          vault root (default ~/vault)
#   VAULT_PROJECTS     folder with project notes (default $VAULT_DIR/projects)
#   VAULT_CONTEXT_MAX  max lines to print (default 80)

VAULT_DIR="${VAULT_DIR:-$HOME/vault}"
PROJECTS="${VAULT_PROJECTS:-$VAULT_DIR/projects}"
MAX="${VAULT_CONTEXT_MAX:-80}"

input="$(cat 2>/dev/null || true)"
cwd="$(printf '%s' "$input" | sed -n 's/.*"cwd"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"
[ -n "$cwd" ] || cwd="$PWD"
[ -d "$PROJECTS" ] || exit 0

root="$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null || echo "$cwd")"
name="$(basename "$root")"
tilde_root="${root/#$HOME/~}"

note=""
# 1. a note whose `repo:` matches this repo (absolute or ~ form)
for f in "$PROJECTS"/*.md; do
  [ -f "$f" ] || continue
  repo_line="$(sed -n '1,/^---$/{/^repo:/p;}' "$f" 2>/dev/null | head -1)"
  repo_val="$(printf '%s' "${repo_line#repo:}" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//; s/^["'\'']//; s/["'\'']$//')"
  [ -n "$repo_val" ] || continue
  if [ "$repo_val" = "$root" ] || [ "$repo_val" = "$tilde_root" ]; then note="$f"; break; fi
done
# 2. fallback: a note named after the repo folder
[ -n "$note" ] || { [ -f "$PROJECTS/$name.md" ] && note="$PROJECTS/$name.md"; }
[ -n "$note" ] || exit 0

echo "## Vault note for this project: ${note#$VAULT_DIR/}"
echo
head -n "$MAX" "$note"
total=$(wc -l < "$note" | tr -d ' ')
[ "$total" -gt "$MAX" ] && echo "… ($((total - MAX)) more lines in the note)"
exit 0
