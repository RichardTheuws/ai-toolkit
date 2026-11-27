# leak-gate

Refuses to publish a folder that contains something private.

We built this repo by copying tools out of private ones. A copy is only safe if
nothing private comes along. Reviewing by eye doesn't hold up: one of our earlier
share lists was approved on titles alone and still leaked a detail. So the
check is a script that refuses the whole publish on a single hit, and it runs
before every push.

## What it checks

1. **Files that never belong in public**: `.env*` (except `.env.example`), `*.bak`, keys and certificates, `credentials/`, `secrets/`, `uploads/`.
2. **Generic patterns**: absolute home paths (`/Users/<name>/`, `/home/<name>/`), Tailscale and LAN IPs, email addresses, IBANs, private keys, common API key shapes.
3. **Your own denylist**: client names, family names, internal host names, project names. One term per line, matched case-insensitively as a whole word, in file contents and file names.
4. **gitleaks**, if installed, for everything secret-shaped the patterns miss.

The denylist itself is the most private file of all, so it lives **outside** the
repo: `~/.config/ai-toolkit/denylist.txt`, or wherever `AI_TOOLKIT_DENYLIST` points.
In CI it comes from a repository secret, and `--ci` hides the matched terms in the log.

## Use it

```bash
python3 leak-gate.py /path/to/folder        # exit 0 clean, 1 hits, 2 usage error
python3 leak-gate.py --ci .                 # same, but without printing denylist terms
```

As a pre-push hook in your repo:

```bash
cat > .git/hooks/pre-push <<'HOOK'
#!/bin/sh
exec python3 scripts/leak-gate/leak-gate.py .
HOOK
chmod +x .git/hooks/pre-push
```

A deliberate exception: put `leak-gate: allow` on that line, with a reason.

Example denylist:

```
# clients
acmecorp
# people
jane
# hosts
prod-mini
```

Python 3.8+, no packages. `brew install gitleaks` recommended.

## Test

```bash
python3 test_leak_gate.py
```

## Known limits

- A denylist only finds what you thought of. It is a net, not a guarantee; read the diff too.
- Whole-word matching means `acme` does not catch `acmecorp`. Add both if you need both.
- It checks the working tree, not git history. Start public repos from a fresh copy, never from a private repo's history.

## Make this better

What do you check before you publish? Tell us in the
[discussions](https://github.com/RichardTheuws/ai-toolkit/discussions).
