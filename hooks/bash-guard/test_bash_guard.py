#!/usr/bin/env python3
"""Tests for bash-guard.py. Run: python3 test_bash_guard.py"""
import json
import pathlib
import subprocess
import sys

GUARD = pathlib.Path(__file__).with_name("bash-guard.py")

# (command, expected to be blocked?)
CASES = [
    # R1: the real incidents
    ('EXCL="--exclude=.env --exclude=node_modules"; rsync -rc --delete $EXCL ./ prod:/srv/app/', True),
    ("rsync -rc --delete ./ prod:/srv/www/projects/portal/", True),
    ("rsync -rc --delete $RSYNC_OPTS ./ prod:/srv/app/", True),
    # R1: safe
    ("rsync -rc --delete --filter='P .env*' --exclude='.env*' ./ prod:/srv/app/", False),
    ("rsync -rc --delete --exclude='.env*' --exclude=node_modules ./ prod:/srv/app/", False),
    ("rsync -rcn --delete --itemize-changes ./ prod:/srv/app/ | head -40", False),
    ("rsync -rc --delete --dry-run ./ prod:/srv/app/", False),
    ('excl=(--exclude=.env --exclude=node_modules); rsync -rc --delete "${excl[@]}" ./ prod:/srv/app/', False),
    ("rsync -a --delete dist/ build/", False),  # local
    ("rsync -avz ./site/ prod:/srv/www/", False),  # no --delete
    ('rsync -a "$SRC/" prod:/srv/x/', False),  # quoted path variable
    ('X="--exclude node_modules --exclude .env"; rsync -az --delete $X ./ prod:/srv/p/', True),
    ("rsync -az --delete dist/ prod:/srv/www/site-static/", False),  # static build
    ("rsync -a --delete prod:/srv/plugins/acf ./local/", False),  # pulling
    ("rsync -a --delete --exclude outputs ./ prod:/tmp/staging-test/", True),  # project folder without .env protection
    # R2
    ("for i in api worker; do docker tag app-$i:latest app-$i:pre-1; done", True),
    ('curl -s -u "$CM_API_KEY:x" https://api.example.com', False),  # :x does not modify
    ('curl -X POST "$D/$ID:fetch"', False),  # :f does not modify
    ("docker tag $s:latest $s:rollback", True),
    ("ssh prod 'docker tag $img:latest $img:prev'", True),
    ("chown $USER:staff file", True),
    ("docker tag ${s}:latest ${s}:rollback", False),
    ("scp f $HOST:/tmp/", False),
    ("echo ${PATH}:x", False),
    # R3
    ("npm test; git commit -m 'x'", True),
    ("npx playwright test\ngit add -A && git commit -m x", True),
    ("npm run build; ./scripts/deploy.sh prod", True),
    ("npm test && git commit -m 'x; y'", False),
    ("set -e\nnpm test\ngit commit -m x", False),
    ("npm run build && ./scripts/deploy.sh prod", False),
    ("git status; git log --oneline -3", False),
    ("npm test || true; echo done", False),
    # override
    ("rsync -rc --delete ./ prod:/srv/app/  # guard-ok: intentional mirror", False),
    ("ls -la; cat VERSION", False),
]


def run(cmd):
    p = subprocess.run([sys.executable, str(GUARD)], input=json.dumps({"tool_input": {"command": cmd}}),
                       capture_output=True, text=True)
    return p.returncode == 2, p.stderr


fails = 0
for cmd, want in CASES:
    got, err = run(cmd)
    ok = got == want
    fails += not ok
    print(("PASS" if ok else "FAIL"), "block" if want else "pass ", "|", cmd.replace("\n", "\\n")[:90])
    if not ok:
        print("     stderr:", err.strip()[:200])
print(f"\n{len(CASES) - fails}/{len(CASES)} passed")
sys.exit(1 if fails else 0)
