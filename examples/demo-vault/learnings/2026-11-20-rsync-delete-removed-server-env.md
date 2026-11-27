---
type: learning
project: acme-shop
date: 2026-11-20
learning_type: anti-pattern
title: "rsync --delete removed the server's .env"
tags: [learning, acme-shop, anti-pattern]
---

# rsync --delete removed the server's .env

**What happened**: a deploy with `rsync --delete` mirrored the repo to the server. The `.env` only existed on the server, so rsync deleted it and the API started without secrets.

**Lesson**: never `rsync --delete` to a server without `--filter='P .env*'`, and dry-run first.

**Root cause**: the deploy command was typed from memory instead of taken from DEPLOY.md.

**How to apply**: every rsync to a server. This came back twice, so it became a hook (bash-guard).
