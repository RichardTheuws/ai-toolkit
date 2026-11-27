#!/usr/bin/env python3
"""Tests for leak-gate.py. Run: python3 scripts/leak-gate/test_leak_gate.py"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

GATE = Path(__file__).with_name("leak-gate.py")

# (file name, content, expected to be blocked?)
CASES = [
    ("clean.md", "Install with `cp hook.py ~/.claude/hooks/`.\n", False),
    ("home.md", "Run /Users/alice/project/deploy.sh\n", True),  # leak-gate: allow (fake test fixture)
    ("home-ok.md", "Replace /Users/you/ with your own home.\n", False),
    ("linux.md", "cd /home/bob/code\n", True),  # leak-gate: allow (fake test fixture)
    ("ci.md", "cd /home/runner/work\n", False),
    ("ts.md", "ssh 100.101.5.7\n", True),  # leak-gate: allow (fake test fixture)
    ("lan.md", "open http://192.168.1.20:8080\n", True),  # leak-gate: allow (fake test fixture)
    ("public-ip.md", "1.1.1.1 is fine\n", False),
    ("mail.md", "Contact jane@acme.io\n", True),  # leak-gate: allow (fake test fixture)
    ("mail-ok.md", "Use you@example.com or 123+x@users.noreply.github.com\n", False),
    ("iban.md", "Pay to NL91ABNA0417164300\n", True),  # leak-gate: allow (fake test fixture)
    ("key.md", "ANTHROPIC_API_KEY=sk-ant-abcdefghijklmnopqrstuvwxyz012345\n", True),  # leak-gate: allow (fake test fixture)
    ("deny.md", "This was built for Acmecorp last year.\n", True),
    ("deny-partial.md", "acmecorporation is a different word\n", False),
    ("allowed.md", "Built for Acmecorp  <!-- leak-gate: allow (public case study) -->\n", False),
    (".env", "X=1\n", True),
    (".env.example", "X=\n", False),
    ("notes.bak", "old\n", True),
    ("acmecorp-notes.txt", "harmless\n", True),
]


def run_case(name, content):
    with tempfile.TemporaryDirectory() as d:
        root = Path(d) / "repo"
        root.mkdir()
        (root / name).write_text(content)
        deny = Path(d) / "denylist.txt"
        deny.write_text("# test\nacmecorp\n")
        env = dict(os.environ, AI_TOOLKIT_DENYLIST=str(deny), PATH="/usr/bin:/bin")  # no gitleaks
        p = subprocess.run([sys.executable, str(GATE), str(root)], capture_output=True, text=True, env=env)
        return p.returncode, p.stderr


def run_ci_mask():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d) / "repo"
        root.mkdir()
        (root / "a.md").write_text("acmecorp\n")
        deny = Path(d) / "deny.txt"
        deny.write_text("acmecorp\n")
        env = dict(os.environ, AI_TOOLKIT_DENYLIST=str(deny), PATH="/usr/bin:/bin")
        p = subprocess.run([sys.executable, str(GATE), "--ci", str(root)], capture_output=True, text=True, env=env)
        return p.returncode == 1 and "acmecorp" not in p.stderr.split("refusing:")[1]


fails = 0
for name, content, want in CASES:
    code, err = run_case(name, content)
    got = code == 1
    ok = got == want
    fails += not ok
    print("PASS" if ok else "FAIL", "block" if want else "pass ", "|", name)
    if not ok:
        print("     ", err.strip()[:300])
ok = run_ci_mask()
fails += not ok
print("PASS" if ok else "FAIL", "--ci hides the matched term")
total = len(CASES) + 1
print(f"\n{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
