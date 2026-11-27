#!/usr/bin/env python3
"""
bash-guard.py: a Claude Code PreToolUse hook on Bash that blocks three shell
mistakes which kept coming back even after we wrote them down as lessons.

  R1  `rsync --delete` to a server without protecting .env, or with options
      passed through a string variable that zsh does not split
      (this once wiped a production .env).
  R2  a zsh modifier straight after a bare variable: `$s:latest`, `$USER:staff`
      (zsh reads `:l`, `:s`, ... as modifiers, so `$tag:latest` is not what you typed).
  R3  a test/build step followed by commit/push/deploy via `;` or a new line,
      without `set -e`: the failure is masked and something goes live anyway.

Blocking = exit 2 with the reason on stderr; Claude sees it and fixes the command.
Allow one command on purpose with `# guard-ok: <reason>` in the command.
Switch it off for a session: export CLAUDE_BASH_GUARD=0

Tests: python3 test_bash_guard.py
"""
import json
import os
import re
import sys


def strip_heredocs(cmd: str) -> str:
    """Drop heredoc bodies (Python/JSON/scripts inside them are data, not shell)."""
    out, lines, i = [], cmd.split("\n"), 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        m = re.search(r"<<-?\s*['\"]?([A-Za-z_]\w*)['\"]?", line)
        i += 1
        if m:
            delim = m.group(1)
            while i < len(lines) and lines[i].strip() != delim:
                i += 1
            if i < len(lines):
                out.append(lines[i])
                i += 1
    return "\n".join(out)


def strip_quoted(cmd: str) -> str:
    """Replace the inside of '...' and "..." with x's so ; and # inside quotes don't count."""
    out, i, n = [], 0, len(cmd)
    while i < n:
        c = cmd[i]
        if c in ("'", '"'):
            j = i + 1
            while j < n and cmd[j] != c:
                if c == '"' and cmd[j] == "\\":
                    j += 1
                j += 1
            out.append(c + "x" * max(0, min(j, n) - i - 1) + (c if j < n else ""))
            i = j + 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def rsync_segments(cmd: str):
    """Each piece from 'rsync' up to the next && || ; | or newline (outside quotes)."""
    plain = strip_quoted(cmd)
    for m in re.finditer(r"(?<![\w-])rsync\s", plain):
        start = m.start()
        end_m = re.search(r"&&|\|\||;|\||\n", plain[start:])
        end = start + end_m.start() if end_m else len(cmd)
        yield cmd[start:end], plain[start:end]


def check_rsync(cmd: str):
    problems = []
    # Variables holding several options, assigned in the same command
    multi_opt_vars = set(
        re.findall(r"\b([A-Za-z_]\w*)=([\"'])[^\"']*--\w[^\"']*\s--\w[^\"']*\2", cmd)
    )
    multi_opt_vars = {name for name, _ in multi_opt_vars}
    for raw, plain in rsync_segments(cmd):
        # R1b: option variable that zsh does not split
        for v in re.findall(r"(?<![\"\w])\$\{?([A-Za-z_]\w*)\}?(?!\[)", raw):
            if v in multi_opt_vars or re.search(r"EXCL|OPT|FLAG|ARGS|FILTER", v, re.I):
                problems.append(
                    f"R1 rsync gets its options through ${v}: zsh does not split a string variable, "
                    "so rsync sees one argument and your excludes do nothing. "
                    "Use an array: excl=(--exclude=.env ...) and then \"${excl[@]}\"."
                )
        if not re.search(r"--delete", raw):
            continue
        tokens = [t.strip("'\"") for t in raw.split()[1:]]
        paths = [t for t in tokens if not t.startswith("-") and not re.match(r"^\w+=", t)]
        if len(paths) < 2:
            continue
        src, dest = paths[-2], paths[-1]
        # only pushing TO a server counts; pulling from a server does not
        if not re.match(r"^[\w.@-]+:", dest) or re.match(r"^[\w.@-]+:", src):
            continue
        # mirroring build output to a static web root is intended; a project folder is not
        if re.search(r"(?:^|/)(?:dist|build|out|public|_site|theme|highscores)/?$", src):
            continue
        dry = re.search(r"(?:^|\s)-[a-zA-Z]*n[a-zA-Z]*(?:\s|$)|--dry-run", plain)
        if dry:
            continue
        # across the whole command: excludes often live in an array before the rsync
        protects_env = re.search(r"--filter=?\s*['\"]?P\s+\S*\.env|-f\s*['\"]?P\s+\S*\.env", cmd) or re.search(
            r"--exclude[= ]\s*['\"]?[^\s'\"]*\.env", cmd
        ) or re.search(r"--exclude-from|--filter=?\s*['\"]?merge|--filter=?\s*['\"]?\.", cmd)
        if not protects_env:
            problems.append(
                "R1 rsync --delete to a server without protecting .env. "
                "Take the command literally from your DEPLOY.md (or deploy script), "
                "add --filter='P .env*' and run it first with -n --itemize-changes."
            )
    return problems


def check_zsh_modifier(cmd: str):
    # $name followed by :<letter>; ${name}:x is safe, and so is $name:/path.
    # Local single quotes don't protect you: through ssh '...' the remote zsh still reads it.
    hits = re.findall(r"(?<![\\$])\$([A-Za-z_]\w*):([acehlqrstuAQP])", cmd)  # measured: only these letters modify
    hits = [(v, m) for v, m in hits if not re.search(r"\$\{?" + v + r"\}?:" + m + r"\w*\}", cmd)]
    if hits:
        v, m = hits[0]
        return [
            f"R2 `${v}:{m}…`: zsh reads `:{m}` as a modifier on ${v}, not as text. "
            f"Write `${{{v}}}:{m}…`."
        ]
    return []


# Only in command position (start of a link in the chain), not as a loose word.
GATE = re.compile(r"^(?:npm|pnpm|yarn|npx|bun)\s+(?:run\s+)?(?:test|build|lint|check|typecheck|e2e)\b"
                  r"|^npx\s+(?:playwright|vitest|jest|tsc|astro\s+check)\b"
                  r"|^(?:\S*/)?(?:pytest|vitest|jest|tsc|bats|tests?\.sh|run-tests\S*)\b"
                  r"|^\S*python3?\s+-m\s+pytest\b")
SHIP = re.compile(r"^(?:git\s+commit|git\s+push|(?:\S*/)?deploy[\w.-]*|docker\s+compose\s+up|rsync)\b")


def links(segment: str):
    """The links of an &&/|| chain, each stripped of leading env assignments."""
    for part in re.split(r"&&|\|\|", segment):
        w = part.strip()
        w = re.sub(r"^(?:[A-Za-z_]\w*=\S*\s+)+", "", w)
        yield w


def check_masked_failure(cmd: str):
    plain = strip_quoted(cmd)
    if re.search(r"\bset\s+-[a-z]*e", plain):
        return []
    parts = [p for p in re.split(r";|\n", plain) if p.strip() and not p.strip().startswith("#")]
    gate_open = False
    for p in parts:
        chain = list(links(p))
        if gate_open and any(SHIP.search(w) for w in chain):
            return [
                "R3 a test/build step is followed by commit/push/deploy via `;` or a new line. "
                "If the test fails, the rest still runs. "
                "Run the tests in their own call and commit only when green, or chain with && "
                "(with `set -o pipefail` if a | grep follows)."
            ]
        last = chain[-1] if chain else ""
        if GATE.search(last) and "||" not in p:
            gate_open = True
    return []


def main():
    if os.environ.get("CLAUDE_BASH_GUARD", "1") == "0":
        return 0
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    cmd = (payload.get("tool_input") or {}).get("command") or ""
    if not cmd or "guard-ok" in cmd:
        return 0
    cmd = strip_heredocs(cmd)
    problems = check_rsync(cmd) + check_zsh_modifier(cmd) + check_masked_failure(cmd)
    if problems:
        print("bash-guard blocked this command:\n- " + "\n- ".join(problems)
              + "\n(On purpose? Add `# guard-ok: <reason>`.)", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
