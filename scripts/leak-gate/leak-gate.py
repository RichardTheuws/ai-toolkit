#!/usr/bin/env python3
"""
leak-gate.py: refuse to publish a folder if it contains anything private.

We built this toolkit by copying tools out of private repos. A copy is only safe
if nothing private comes along: secrets, absolute home paths, internal host
names, client names, family names. This gate checks a folder and exits 1 on the
first category of hits, so you can run it as a pre-push hook and in CI.

Checks:
  1. Forbidden files: .env*, *.bak, *.pem, *.key, credentials/, uploads/
  2. Generic patterns: absolute home paths, private/Tailscale IPs, email
     addresses, IBANs, private keys, common API-key shapes
  3. Your own denylist: one term per line, matched case-insensitively as a
     whole word. Keep this file OUTSIDE the repo (default
     ~/.config/ai-toolkit/denylist.txt, or set AI_TOOLKIT_DENYLIST). In CI,
     pass it through a secret.
  4. gitleaks, if it is installed (optional, recommended)

Usage:
  leak-gate.py [PATH]            # default: current directory
  leak-gate.py --ci [PATH]       # hide matched denylist terms in the output

Allowed exceptions: put `leak-gate: allow` on the same line, with a reason.

Exit codes: 0 clean, 1 hits found, 2 usage error.
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "dist", "__pycache__", ".venv"}
FORBIDDEN_FILES = [
    (re.compile(r"(^|/)\.env(\.|$)(?!example)"), ".env file"),
    (re.compile(r"\.bak$|\.orig$|~$"), "backup file"),
    (re.compile(r"\.(pem|key|p12|pfx)$"), "key or certificate"),
    (re.compile(r"(^|/)(credentials|secrets|uploads)(/|$)"), "credentials or uploads folder"),
]
PATTERNS = [
    (re.compile(r"/Users/(?!you/|<you>|\$USER|example/)[A-Za-z0-9._-]+/"), "absolute macOS home path"),
    (re.compile(r"/home/(?!you/|<you>|\$USER|example/|runner/)[a-z0-9._-]+/"), "absolute Linux home path"),
    (re.compile(r"\b100\.(6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b"), "Tailscale (CGNAT) IP"),
    (re.compile(r"\b(10\.\d{1,3}|192\.168|172\.(1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b"), "private LAN IP"),
    (re.compile(r"[A-Za-z0-9._%+-]+@(?!example\.(com|org)|users\.noreply\.github\.com|anthropic\.com)"
                r"[A-Za-z0-9.-]+\.[a-z]{2,}\b"), "email address"),
    (re.compile(r"\b[A-Z]{2}\d{2}[A-Z]{4}\d{10}\b"), "IBAN"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key"),
    (re.compile(r"\b(sk-ant-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{32,}|ghp_[A-Za-z0-9]{30,}|"
                r"AKIA[0-9A-Z]{16}|xox[bpa]-[A-Za-z0-9-]{20,}|AIza[0-9A-Za-z_-]{35})\b"), "API key"),
]
ALLOW = "leak-gate: allow"
TEXT_LIMIT = 2_000_000


def load_denylist():
    path = Path(os.environ.get("AI_TOOLKIT_DENYLIST", "~/.config/ai-toolkit/denylist.txt")).expanduser()
    if not path.exists():
        return path, []
    terms = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            terms.append(line)
    return path, terms


def files_under(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            yield Path(dirpath) / name


def read_text(path: Path):
    try:
        if path.stat().st_size > TEXT_LIMIT:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data[:4096]:
        return None
    return data.decode("utf-8", errors="replace")


def main(argv):
    ci = "--ci" in argv
    args = [a for a in argv if not a.startswith("--")]
    root = Path(args[0] if args else ".").resolve()
    if not root.is_dir():
        print(f"leak-gate: not a folder: {root}", file=sys.stderr)
        return 2
    deny_path, terms = load_denylist()
    deny_re = [(t, re.compile(r"(?<![\w])" + re.escape(t) + r"(?![\w])", re.I)) for t in terms]
    hits = []
    me = Path(__file__).resolve()

    for path in files_under(root):
        rel = path.relative_to(root).as_posix()
        for rx, label in FORBIDDEN_FILES:
            if rx.search(rel):
                hits.append(f"{rel}: forbidden file ({label})")
        if path.resolve() == me:
            continue  # this file contains the patterns themselves
        text = read_text(path)
        if text is None:
            continue
        for term, rx in deny_re:
            if rx.search(rel):
                hits.append(f"{rel}: file name matches denylist term" + ("" if ci else f" '{term}'"))
        for n, line in enumerate(text.splitlines(), 1):
            if ALLOW in line:
                continue
            for rx, label in PATTERNS:
                if rx.search(line):
                    hits.append(f"{rel}:{n}: {label}")
            for term, rx in deny_re:
                if rx.search(line):
                    hits.append(f"{rel}:{n}: denylist term" + ("" if ci else f" '{term}'"))

    if shutil.which("gitleaks"):
        p = subprocess.run(["gitleaks", "dir", str(root), "--no-banner", "--redact", "-v"],
                           capture_output=True, text=True)
        if p.returncode == 1:
            hits.append("gitleaks found secrets:\n" + (p.stdout or p.stderr).strip()[:4000])
    else:
        print("leak-gate: gitleaks not installed, skipping secret scan (brew install gitleaks)", file=sys.stderr)

    if not terms:
        print(f"leak-gate: no denylist at {deny_path}; only generic checks ran", file=sys.stderr)

    if hits:
        print(f"leak-gate: {len(hits)} hit(s), refusing:", file=sys.stderr)
        for h in hits:
            print("  " + h, file=sys.stderr)
        return 1
    print(f"leak-gate: clean ({root.name}, {len(terms)} denylist terms)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
