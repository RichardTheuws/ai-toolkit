#!/usr/bin/env bash
# Tests for vault-context.sh. Run: bash test_vault_context.sh
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; HOOK="$HERE/vault-context.sh"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
pass=0; fail=0
ok() { if eval "$2"; then pass=$((pass+1)); echo "PASS $1"; else fail=$((fail+1)); echo "FAIL $1"; fi; }

mkdir -p "$T/vault/projects" "$T/code/acme-shop" "$T/code/other" "$T/code/named"
git -C "$T/code/acme-shop" init -q; git -C "$T/code/other" init -q; git -C "$T/code/named" init -q
root="$(cd "$T/code/acme-shop" && pwd -P)"
printf -- '---\ntype: project\nrepo: %s\n---\n# Acme shop\nStatus: building checkout\n' "$root" > "$T/vault/projects/shop.md"
printf -- '---\ntype: project\n---\n# Named by folder\n' > "$T/vault/projects/named.md"
{ printf -- '---\nrepo: x\n---\n'; for i in $(seq 1 200); do echo "line $i"; done; } > "$T/vault/projects/long.md"

run() { printf '{"cwd":"%s"}' "$1" | VAULT_DIR="$T/vault" VAULT_CONTEXT_MAX="${2:-80}" bash "$HOOK"; }

out="$(run "$root")";            ok "matches on repo: frontmatter" '[[ "$out" == *"building checkout"* ]]'
out="$(run "$root/")";           ok "works from inside the repo" '[[ "$out" == *"Acme shop"* ]]'
out="$(run "$T/code/named")";    ok "falls back to the folder name" '[[ "$out" == *"Named by folder"* ]]'
out="$(run "$T/code/other")";    ok "prints nothing without a note" '[ -z "$out" ]'
out="$(printf '{"cwd":"%s"}' "$root" | VAULT_DIR="$T/nope" bash "$HOOK"; echo "exit=$?")"; ok "missing vault exits 0 silently" '[ "$out" = "exit=0" ]'
printf -- '---\nrepo: %s\n---\n' "$root" > /dev/null
cp "$T/vault/projects/long.md" "$T/vault/projects/acme-long.md"; sed -i.x "s#^repo: x#repo: $T/code/long#" "$T/vault/projects/acme-long.md"; rm -f "$T/vault/projects/acme-long.md.x"
mkdir -p "$T/code/long"; git -C "$T/code/long" init -q
out="$(run "$(cd "$T/code/long" && pwd -P)" 20)"; ok "caps long notes" '[[ "$out" == *"more lines in the note"* ]]'
out="$(echo 'not json' | VAULT_DIR="$T/vault" bash "$HOOK"; echo "exit=$?")"; ok "bad input exits 0" '[[ "$out" == *"exit=0"* ]]'
echo; echo "$pass/$((pass+fail)) passed"; [ "$fail" = 0 ]
