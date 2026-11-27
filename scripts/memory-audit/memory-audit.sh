#!/usr/bin/env bash
#
# memory-audit.sh: check a project's Claude Code auto-memory for bloat.
#
# Claude Code loads MEMORY.md into every session. When it grows into a manual
# instead of an index, every session pays for it. This script scores the memory
# of one project green / orange / red and says what to do about it.
#
# It flags:
#   - MEMORY.md over 80 (orange) or 150 (red) lines
#   - sections with no pointer to a *.md file (detail written inline)
#   - sections over 10 lines that are not a plain pointer list
#   - session logs in memory (## Last session / ## Next session)
#   - version stamps in section titles (vX.Y.Z belongs in a changelog)
#   - stale session-*.md files (>30 days)
#   - orphans: memory files not reachable from MEMORY.md, also not via an index
#
# It understands a "router" setup: MEMORY.md points to a few index files, each
# index points to detail files. Then the total file count says little about
# context cost, so it measures the largest index instead.
#
# Usage:
#   memory-audit.sh                    # human-readable
#   memory-audit.sh --quiet            # verdict + actions only
#   memory-audit.sh --json             # machine-readable
#   memory-audit.sh --strict           # exit 1 on red
#   memory-audit.sh --project-dir PATH # audit another project
#
# Exit codes: 0 green/orange, 1 red (only with --strict), 2 error,
#             3 no memory dir or MEMORY.md (only with --strict)

set -euo pipefail

STRICT=false
QUIET=false
JSON=false
PROJECT_DIR="${PWD}"

while [ $# -gt 0 ]; do
  case "$1" in
    --strict) STRICT=true ;;
    --quiet)  QUIET=true ;;
    --json)   JSON=true; QUIET=true ;;
    --project-dir=*) PROJECT_DIR="${1#*=}" ;;
    --project-dir) shift; PROJECT_DIR="${1:-$PWD}" ;;
    -h|--help)
      sed -n '2,31p' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
  esac
  shift
done

# Resolve symlinks and on-disk casing; a mismatch would derive the wrong slug
# and silently skip the audit.
PROJECT_DIR="$(cd "$PROJECT_DIR" 2>/dev/null && pwd -P || echo "$PROJECT_DIR")"

# Claude Code replaces every non-alphanumeric character in the project path
# with '-' to name the memory folder (spaces too, not only slashes).
derive_memory_dir() {
  local slug
  slug="$(echo "$1" | sed 's|[^a-zA-Z0-9]|-|g')"
  echo "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/projects/${slug}/memory"
}

MEMORY_DIR="$(derive_memory_dir "$PROJECT_DIR")"
MEMORY_FILE="$MEMORY_DIR/MEMORY.md"

if [ ! -d "$MEMORY_DIR" ]; then
  if [ "$JSON" = true ]; then
    printf '{"verdict":"none","reason":"no memory dir","path":"%s"}\n' "$MEMORY_DIR"
  else
    echo "No auto-memory folder for this project: $MEMORY_DIR" >&2
    echo "(No Claude Code sessions from this path yet, or a path mismatch. Resolved path: $PROJECT_DIR)" >&2
  fi
  [ "$STRICT" = true ] && exit 3
  exit 0
fi

if [ ! -f "$MEMORY_FILE" ]; then
  if [ "$JSON" = true ]; then
    printf '{"verdict":"none","reason":"no MEMORY.md","path":"%s"}\n' "$MEMORY_FILE"
  else
    echo "No MEMORY.md in $MEMORY_DIR" >&2
  fi
  [ "$STRICT" = true ] && exit 3
  exit 0
fi

LINES=$(wc -l < "$MEMORY_FILE" | tr -d ' ')
FILES=$(find "$MEMORY_DIR" -maxdepth 1 -name '*.md' -type f | wc -l | tr -d ' ')
H2_COUNT=$(grep -c '^## ' "$MEMORY_FILE" || true)

H2_NO_LINK=()
H2_OVERLONG=()
H2_VERSIONED=()
SESSION_IN_MEMORY=false

# Section titles that may hold short inline notes without a pointer.
SPEC_H2_PATTERN='^## (Architecture|Active projects|Lessons|Technical reference|Preferences|Applies everywhere)$'

current=""
buffer=""
buffer_lines=0
buffer_pointer_lines=0
flush() {
  if [ -n "$current" ]; then
    if ! grep -qE '\[[^]]+\]\([^)]+\.md\)' <<<"$buffer"; then
      if ! grep -qiE "$SPEC_H2_PATTERN" <<<"$current"; then
        H2_NO_LINK+=("$current")
      fi
    fi
    # Overlong: skip if the section is a pointer list (>80% of bullets are pointers)
    if [ "$buffer_lines" -gt 10 ]; then
      local bullet_lines pointer_ratio
      bullet_lines=$(grep -cE '^- ' <<<"$buffer" || true)
      if [ "$bullet_lines" -gt 0 ]; then
        pointer_ratio=$(( buffer_pointer_lines * 100 / bullet_lines ))
      else
        pointer_ratio=0
      fi
      if [ "$pointer_ratio" -lt 80 ]; then
        H2_OVERLONG+=("$current ($buffer_lines lines)")
      fi
    fi
    if grep -qE 'v[0-9]+\.[0-9]+\.[0-9]+' <<<"$current"; then
      H2_VERSIONED+=("$current")
    fi
    if grep -qiE '^## (Last|Next|Previous) session' <<<"$current"; then
      SESSION_IN_MEMORY=true
    fi
  fi
}

while IFS= read -r line || [ -n "$line" ]; do
  if [[ "$line" =~ ^##\  ]]; then
    flush
    current="$line"
    buffer=""
    buffer_lines=0
    buffer_pointer_lines=0
  else
    buffer+="$line"$'\n'
    [ -n "$line" ] && buffer_lines=$((buffer_lines + 1))
    # Pointer line: `- [Title](file.md) — hook` (em dash or plain dash)
    if [[ "$line" =~ ^-\ \[.+\]\(.+\.md\)\ (—|-)\ .+ ]]; then
      buffer_pointer_lines=$((buffer_pointer_lines + 1))
    fi
  fi
done < "$MEMORY_FILE"
flush

STALE_SESSIONS=()
while IFS= read -r f; do
  [ -z "$f" ] && continue
  STALE_SESSIONS+=("$(basename "$f")")
done < <(find "$MEMORY_DIR" -maxdepth 1 -name 'session-*.md' -mtime +30 2>/dev/null)

# Orphans = files NOT reachable from MEMORY.md. Reachability is transitive:
# MEMORY.md may point to index files that point to detail files. A one-level
# check would flag every file routed through an index (false red, exactly
# where the memory is healthy).
REACHABLE=$'MEMORY.md\n'
FRONTIER="MEMORY.md"
while [ -n "$FRONTIER" ]; do
  NEXT=""
  while IFS= read -r node; do
    [ -z "$node" ] && continue
    [ -f "$MEMORY_DIR/$node" ] || continue
    while IFS= read -r ref; do
      [ -z "$ref" ] && continue
      [ -f "$MEMORY_DIR/$ref" ] || continue
      if grep -qxF "$ref" <<<"$REACHABLE"; then continue; fi
      REACHABLE+="$ref"$'\n'
      NEXT+="$ref"$'\n'
    done < <(grep -oE '[A-Za-z0-9._-]+\.md' "$MEMORY_DIR/$node" 2>/dev/null | sort -u || true)
  done <<<"$FRONTIER"
  FRONTIER="$NEXT"
done

# Index files = files named in MEMORY.md that point to >=3 other memory files.
# Two or more means a router setup, where a higher file count is by design.
INDEX_COUNT=0
INDEX_MAX_LINES=0
INDEX_MAX_NAME=""
while IFS= read -r ref; do
  [ -z "$ref" ] && continue
  [ -f "$MEMORY_DIR/$ref" ] || continue
  fanout=0
  while IFS= read -r sub; do
    [ -n "$sub" ] && [ -f "$MEMORY_DIR/$sub" ] && fanout=$((fanout + 1))
  done < <(grep -oE '[A-Za-z0-9._-]+\.md' "$MEMORY_DIR/$ref" 2>/dev/null | sort -u || true)
  if [ "$fanout" -ge 3 ]; then
    INDEX_COUNT=$((INDEX_COUNT + 1))
    idx_lines=$(wc -l < "$MEMORY_DIR/$ref" | tr -d ' ')
    if [ "$idx_lines" -gt "$INDEX_MAX_LINES" ]; then
      INDEX_MAX_LINES=$idx_lines; INDEX_MAX_NAME=$ref
    fi
  fi
done < <(grep -oE '[A-Za-z0-9._-]+\.md' "$MEMORY_FILE" 2>/dev/null | sort -u || true)
ROUTER=false
[ "$INDEX_COUNT" -ge 2 ] && ROUTER=true

ORPHANS=()
while IFS= read -r f; do
  base="$(basename "$f")"
  [ "$base" = "MEMORY.md" ] && continue
  if ! grep -qxF "$base" <<<"$REACHABLE"; then
    ORPHANS+=("$base")
  fi
done < <(find "$MEMORY_DIR" -maxdepth 1 -name '*.md' -type f)

VERDICT="green"
REASONS=()

if [ "$LINES" -gt 150 ]; then VERDICT="red"; REASONS+=("MEMORY.md has $LINES lines (>150)"); fi
# In a router setup a session loads MEMORY.md plus one index; detail files are
# read only when relevant. So measure the largest index with the same 80/150
# limits, and keep the total only as a backstop against unbounded growth.
FILES_RED=30; FILES_ORANGE=15
if [ "$ROUTER" = true ]; then FILES_RED=60; FILES_ORANGE=$FILES_RED; fi
if [ "$FILES" -gt "$FILES_RED" ]; then VERDICT="red"; REASONS+=("$FILES memory files (>$FILES_RED)"); fi
if [ "$ROUTER" = true ] && [ "$INDEX_MAX_LINES" -gt 150 ]; then
  VERDICT="red"; REASONS+=("$INDEX_MAX_NAME has $INDEX_MAX_LINES lines (>150)")
fi
if [ "$SESSION_IN_MEMORY" = true ]; then
  [ "$VERDICT" != "red" ] && VERDICT="orange"
  REASONS+=("session sections in MEMORY.md (git log is the session history)")
fi
if [ "${#STALE_SESSIONS[@]}" -gt 3 ]; then VERDICT="red"; REASONS+=("${#STALE_SESSIONS[@]} stale session-*.md (>30 days)"); fi
if [ "${#ORPHANS[@]}" -gt 2 ];        then VERDICT="red"; REASONS+=("${#ORPHANS[@]} orphans not reachable from MEMORY.md"); fi
if [ "${#H2_OVERLONG[@]}" -gt 0 ] && [ "$VERDICT" = "green" ]; then VERDICT="orange"; REASONS+=("${#H2_OVERLONG[@]} section(s) over 10 lines"); fi
if [ "${#H2_VERSIONED[@]}" -gt 1 ] && [ "$VERDICT" = "green" ]; then VERDICT="orange"; REASONS+=("version stamps in section titles"); fi
if [ "$LINES" -gt 80 ] && [ "$VERDICT" = "green" ]; then VERDICT="orange"; REASONS+=("MEMORY.md has $LINES lines (limit 80)"); fi
if [ "$FILES" -gt "$FILES_ORANGE" ] && [ "$VERDICT" = "green" ]; then VERDICT="orange"; REASONS+=("$FILES memory files (limit $FILES_ORANGE)"); fi
if [ "$ROUTER" = true ] && [ "$INDEX_MAX_LINES" -gt 80 ] && [ "$VERDICT" = "green" ]; then
  VERDICT="orange"; REASONS+=("$INDEX_MAX_NAME has $INDEX_MAX_LINES lines (limit 80)")
fi

if [ "$JSON" = true ]; then
  printf '{"verdict":"%s","lines":%d,"files":%d,"h2_count":%d,' "$VERDICT" "$LINES" "$FILES" "$H2_COUNT"
  printf '"session_in_memory":%s,' "$SESSION_IN_MEMORY"
  printf '"stale_sessions":%d,"orphans":%d,"index_files":%d,"index_max_lines":%d,' "${#STALE_SESSIONS[@]}" "${#ORPHANS[@]}" "$INDEX_COUNT" "$INDEX_MAX_LINES"
  printf '"h2_no_link":%d,"h2_overlong":%d,"h2_versioned":%d,' \
    "${#H2_NO_LINK[@]}" "${#H2_OVERLONG[@]}" "${#H2_VERSIONED[@]}"
  printf '"path":"%s"}\n' "$MEMORY_FILE"
  [ "$STRICT" = true ] && [ "$VERDICT" = "red" ] && exit 1
  exit 0
fi

color_for() {
  [ -t 1 ] || return 0
  case "$1" in
    green)  printf '\033[32m' ;;
    orange) printf '\033[33m' ;;
    red)    printf '\033[31m' ;;
  esac
}
RESET=''; [ -t 1 ] && RESET='\033[0m'

if [ "$QUIET" != true ]; then
  echo "=== Memory audit: $(basename "$PROJECT_DIR") ==="
  echo "Path:    $MEMORY_FILE"
  echo "Lines:   $LINES   Files: $FILES   Sections: $H2_COUNT   Index files: $INDEX_COUNT"
  [ "$ROUTER" = true ] && echo "Router:  largest index $INDEX_MAX_NAME ($INDEX_MAX_LINES lines)"
  echo ""
fi

printf "Verdict: %b%s%b" "$(color_for "$VERDICT")" "$(echo "$VERDICT" | tr '[:lower:]' '[:upper:]')" "$RESET"
case "$VERDICT" in
  green)  echo "  - memory is healthy." ;;
  orange) echo "  - worth a look, not blocking." ;;
  red)    echo "  - consolidate before the next session." ;;
esac
echo ""

if [ "${#REASONS[@]}" -gt 0 ]; then
  echo "Reasons:"
  for r in "${REASONS[@]}"; do echo "  - $r"; done
  echo ""
fi

if [ "$QUIET" != true ]; then
  if [ "${#H2_NO_LINK[@]}" -gt 0 ]; then
    echo "Sections without a *.md pointer (move the detail out, or keep it deliberately inline):"
    for s in "${H2_NO_LINK[@]}"; do echo "  $s"; done
    echo ""
  fi
  if [ "${#H2_OVERLONG[@]}" -gt 0 ]; then
    echo "Sections over 10 lines (move to their own file):"
    for s in "${H2_OVERLONG[@]}"; do echo "  $s"; done
    echo ""
  fi
  if [ "${#H2_VERSIONED[@]}" -gt 0 ]; then
    echo "Sections with a version stamp (versions belong in a changelog):"
    for s in "${H2_VERSIONED[@]}"; do echo "  $s"; done
    echo ""
  fi
  if [ "${#STALE_SESSIONS[@]}" -gt 0 ]; then
    echo "Stale session-*.md (>30 days, consider deleting):"
    for s in "${STALE_SESSIONS[@]}"; do echo "  $s"; done
    echo ""
  fi
  if [ "${#ORPHANS[@]}" -gt 0 ]; then
    echo "Orphans (not reachable from MEMORY.md, not even through an index):"
    for s in "${ORPHANS[@]}"; do echo "  $s"; done
    echo ""
  fi
fi

if [ "$VERDICT" != "green" ]; then
  echo "Suggested actions:"
  [ "$SESSION_IN_MEMORY" = true ] && \
    echo "  - Remove the session sections from MEMORY.md; git log already tells that story."
  [ "${#H2_OVERLONG[@]}" -gt 0 ] && \
    echo "  - Move long sections to <type>_<topic>.md and leave a one-line pointer."
  [ "${#H2_VERSIONED[@]}" -gt 1 ] && \
    echo "  - Drop version stamps from titles."
  [ "${#STALE_SESSIONS[@]}" -gt 0 ] && \
    echo "  - Delete the ${#STALE_SESSIONS[@]} stale session file(s) listed above."
  [ "${#ORPHANS[@]}" -gt 0 ] && \
    echo "  - Add a pointer for each orphan to MEMORY.md or an index, or delete it."
  [ "$LINES" -gt 150 ] && \
    echo "  - MEMORY.md over 150 lines: split into a router + indexes (see playbooks/memory-hygiene.md)."
fi

if [ "$STRICT" = true ] && [ "$VERDICT" = "red" ]; then
  exit 1
fi
exit 0
