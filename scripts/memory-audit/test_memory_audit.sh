#!/usr/bin/env bash
# Tests for memory-audit.sh. Run: bash scripts/memory-audit/test_memory_audit.sh
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
AUDIT="$HERE/memory-audit.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export CLAUDE_CONFIG_DIR="$TMP/claude"
pass=0; fail=0

# make_project <name> -> prints the memory dir for a fresh project folder
make_project() {
  local proj="$TMP/code/$1"
  mkdir -p "$proj"
  proj="$(cd "$proj" && pwd -P)"
  local slug; slug="$(echo "$proj" | sed 's|[^a-zA-Z0-9]|-|g')"
  mkdir -p "$CLAUDE_CONFIG_DIR/projects/$slug/memory"
  echo "$proj"
}
memdir() { local slug; slug="$(echo "$1" | sed 's|[^a-zA-Z0-9]|-|g')"; echo "$CLAUDE_CONFIG_DIR/projects/$slug/memory"; }

expect() { # expect <name> <project> <verdict>
  local got; got="$(bash "$AUDIT" --json --project-dir "$2" | sed -E 's/.*"verdict":"([a-z]+)".*/\1/')"
  if [ "$got" = "$3" ]; then pass=$((pass+1)); echo "PASS $1 ($got)"; else fail=$((fail+1)); echo "FAIL $1: want $3, got $got"; fi
}

# 1. small, clean index
p="$(make_project clean)"; m="$(memdir "$p")"
cat > "$m/MEMORY.md" <<'EOF'
# acme-shop
- [Deploy](reference_deploy.md) — how we ship
- [Tone](feedback_tone.md) — short sentences
EOF
echo "deploy" > "$m/reference_deploy.md"; echo "tone" > "$m/feedback_tone.md"
expect "clean index" "$p" green

# 2. session section in memory
p="$(make_project session)"; m="$(memdir "$p")"
printf '# x\n## Last session\nWe did things.\n' > "$m/MEMORY.md"
expect "session section" "$p" orange

# 3. too long
p="$(make_project long)"; m="$(memdir "$p")"
{ echo "# x"; for i in $(seq 1 160); do echo "line $i"; done; } > "$m/MEMORY.md"
expect "over 150 lines" "$p" red

# 4. orphans
p="$(make_project orphans)"; m="$(memdir "$p")"
echo "# x" > "$m/MEMORY.md"; for i in 1 2 3; do echo x > "$m/note_$i.md"; done
expect "3 orphans" "$p" red

# 5. router: files reached through an index are not orphans, and 40 files is fine
p="$(make_project router)"; m="$(memdir "$p")"
printf '# router\n- [Shop](INDEX-shop.md) — shop work\n- [Ops](INDEX-ops.md) — ops work\n' > "$m/MEMORY.md"
{ echo "# shop"; for i in $(seq 1 20); do echo "- [S$i](shop_$i.md) — s"; echo s > "$m/shop_$i.md"; done; } > "$m/INDEX-shop.md"
{ echo "# ops";  for i in $(seq 1 20); do echo "- [O$i](ops_$i.md) — o";  echo o > "$m/ops_$i.md";  done; } > "$m/INDEX-ops.md"
expect "router with 42 files" "$p" green

# 6. no memory folder
p="$TMP/code/none"; mkdir -p "$p"
out="$(bash "$AUDIT" --json --project-dir "$p")"
if grep -q '"verdict":"none"' <<<"$out"; then pass=$((pass+1)); echo "PASS no memory dir (none)"; else fail=$((fail+1)); echo "FAIL no memory dir: $out"; fi

# 7. path with a space
p="$(make_project "with space")"; m="$(memdir "$p")"
printf '# x\n- [A](a.md) — a\n' > "$m/MEMORY.md"; echo a > "$m/a.md"
expect "path with a space" "$p" green

# 8. --strict exits 1 on red
p="$(make_project strict)"; m="$(memdir "$p")"
{ echo "# x"; for i in $(seq 1 160); do echo "line $i"; done; } > "$m/MEMORY.md"
bash "$AUDIT" --strict --quiet --project-dir "$p" >/dev/null; code=$?
if [ "$code" = 1 ]; then pass=$((pass+1)); echo "PASS --strict exit 1"; else fail=$((fail+1)); echo "FAIL --strict exit $code"; fi

echo ""; echo "$pass/$((pass+fail)) passed"
[ "$fail" = 0 ]
