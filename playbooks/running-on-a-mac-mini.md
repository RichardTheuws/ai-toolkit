# Running Claude-built apps on a Mac mini

We run our own apps and a set of client sites on a Mac mini at home, most of it written with Claude Code. These are the things that went wrong in production, why, and what we do now. Most cost us an outage or an evening before we wrote them down.

**The setup.** A Mac mini M4 runs all containers under Docker Desktop. One shared Caddy container is the reverse proxy for every site. A Cloudflare tunnel (a `cloudflared` container) brings traffic in, so the machine has no open ports to the internet. A second, older Mac mini checks the first one every 15 minutes and makes the nightly backup. The two reach each other over Tailscale. Files also go off-site every night, encrypted with restic.

Each item reads: **symptom**, **cause**, **what we do now**.

## Deploy and rsync

**1. A deploy wiped files that only lived on the server.**
`rsync --delete` removed a secrets folder, and later the production `.env` and its backups. rsync mirrors the source. Anything that is not in the repo looks deleted to it, even when it belongs on the server. Now we protect server-only files and count deletions in a dry run first:

```bash
rsync -rcn --delete --itemize-changes --filter='P .env*' ./ host:/srv/app/ > plan.txt
grep -c '^\*deleting' plan.txt   # must be 0, otherwise stop
```

**2. The excludes were in a shell variable, and none of them applied.**
`EX="--exclude=.env* ..."; rsync $EX ...` works in bash. zsh does not split an unquoted variable, so rsync got one meaningless pattern and ran `--delete` with no exclusions. Now excludes go literally on the command line, quoted, never in a variable. The shell guard hook in this repo ([hooks/bash-guard/](../hooks/bash-guard/)) came from items 1 and 2: it blocks `rsync --delete` to a server without `.env` protection, or with an option-string variable.

**3. rsync replaced the production `docker-compose.yml` with the dev one.**
The production compose file differs on purpose (ports, container names, extra services) and is not in git. Now every rsync excludes `docker-compose.yml`, `.env`, `.env.*` and data folders. To check a restored compose file, compare `docker compose -f <candidate> config --hash "*"` with the `com.docker.compose.config-hash` label of the running containers. Only an equal hash means an exact restore.

**4. The deploy shipped hundreds of MB that were not in git.**
Rendered videos and build artefacts lived on disk but not in git, and rsync took them along. A hand-written exclude list is always one item behind. Now we use the repo's own ignore rules, with explicit secret excludes on top: `--filter=':- .gitignore'`.

**5. Containers failed with `EACCES` after a deploy.**
`rsync -a` keeps the owner from the laptop. That user does not exist inside the container, and the bind mount on macOS enforces it. Now: `rsync --chown=<server-user>:staff ...`, or a `chown -R` before the restart.

**6. A failed deploy reported exit code 0.**
`./deploy.sh > log 2>&1; echo "EXIT=$?"` always ends with the exit code of `echo`. Now we capture the code first (`./deploy.sh; RC=$?`) and never trust exit codes alone: we ask the live app for its version and compare. The bash guard also blocks test-then-commit chained with `;`.

## Docker on macOS

**7. A deploy said "Built" and "Started", but the new route was missing.**
The build failed in an early stage and compose started the previous image under the same tag. Now we grep build output for `error|exit code` instead of reading the last line, and check that the new content exists in the container.

**8. Secrets ended up inside an image.**
Docker reads `.dockerignore`, never `.gitignore`. With `COPY . .` and no `.dockerignore`, the `.env` in the build folder went into the image. Now every Dockerfile gets a `.dockerignore` with `.env`, `.env.*`, `!.env.example`, `.git` and `node_modules`, and we check: `docker run --rm --entrypoint sh <image> -c "ls -la /app/.env"` should say it does not exist.

**9. `docker build` over SSH failed on the keychain.**
Docker Desktop's credential store needs an interactive session to pull base images. Now we build on the laptop (same arm64) and move the image: `docker save <img> | gzip | ssh host 'gunzip | docker load'`, then `docker compose up -d --no-build`. We tag the previous image first as a fallback.

**10. A config file edited on the host stayed old inside the container.**
A single-file bind mount follows the old inode once the file is replaced, and Docker Desktop caches it. Caddy then validated a truncated file. Now we mount the directory, not the file. If a file mount is already there, `docker restart` the container after editing.

**11. Postgres failed with error 53100 while the Mac had plenty of free disk.**
53100 is `disk_full`, and it is about the Docker VM's own virtual disk, not macOS. Build cache and old volumes from all projects pile up there. Now: `docker system df` to look, `docker builder prune -f` is safe. Volumes only after checking, since they hold data.

**12. Containers can't reach broadcast or multicast on the LAN.**
Docker Desktop runs in a VM behind NAT. Wake-on-LAN and mDNS/SSDP discovery don't get through; unicast does. Now we wake devices through something that sits on the LAN itself, and discover with known seed addresses.

**13. No GPU inside containers.**
Docker Desktop on macOS has no Metal passthrough, so models in a container run on the CPU, 5 to 10 times slower. Now local models run natively (Ollama from Homebrew, started by a LaunchAgent), not in Docker.

**14. Named volumes were not in the backup.**
Named volumes live inside the Docker VM, and our backup only covers folders on the host. Now app data is a bind mount into a backed-up folder (`./var/<name>:/data/<name>`), and we check the backup before writing anything about it.

## Caddy

**15. A per-IP rate limit applied to all visitors together.**
Traffic goes Cloudflare → cloudflared → Caddy → app. Caddy trusted no proxy, so every request came from the cloudflared container. Now Caddy has `trusted_proxies` set for the Docker network and passes the visitor address from `CF-Connecting-IP`. Apps read the first `X-Forwarded-For` value, never the socket address.

**16. A broken Caddyfile got reloaded anyway.**
`caddy validate | tail && caddy reload` tests the exit code of `tail`. Now we back up, validate without a pipe, check the exit code, then reload.

**17. Caddy imported rules from a folder a build could write to.**
A broken imported file keeps every site down after a restart; a malicious one can add proxy rules. Now generated rules go through a validator into the infra repo, with an exact path, never a glob into a build folder.

## Cloudflare tunnel

**18. A new ingress rule in `config.yml` did nothing.**
Our tunnel is remote-managed. The local file is ignored; the log line `Updated to new configuration ... version=N` gives that away. Now ingress changes go through the API (see the recipe below). They apply live, without a restart.

**19. `docker kill --signal=HUP cloudflared` took every site down.**
cloudflared treats SIGHUP as shutdown. There is no hot reload. Now: `docker restart` only.

**20. Visitors saw 502s every few hours while the app was healthy.**
The cloudflared log showed `failed to sufficiently increase receive buffer size` and QUIC timeouts. The UDP buffer in the Docker VM is too small for QUIC. Now the tunnel runs over HTTP/2: `tunnel --no-autoupdate --protocol http2 run`.

**21. `cloudflared tunnel route dns` created the wrong record.**
For a hostname outside the zone of `cert.pem`, it appends that zone: `app.other.example` became `app.other.example.example.com`. Now `route dns` only for the cert's own zone. Other zones get the CNAME through the API, and we read the command's output.

**22. A fresh deploy served the old JavaScript.**
Cloudflare caches `.js` and `.css` at the edge for about 4 hours by default; HTML it does not. Now assets get a content hash or version in the file name (`app.3f9c1a2b.js`), referenced from the uncached HTML. For video: `?v=3`. We verify at the CDN, not at the origin.

**23. A page that must never be cached came back as `HIT`.**
Cache rules are not firewall rules. All matching rules apply and the last one wins for a setting. Now exclusions go inside the expression of every caching rule, and we test each path with two requests: the first fills the cache, the second shows whether it caches.

### Recipe: a new subdomain

1. Run the app on the same Docker network as Caddy, or put static files in the web root.
2. Add a site block in Caddy, for example `@app host app.example.com` with `handle @app { reverse_proxy myapp:<port> }`. Back up the Caddyfile, `caddy validate` (check the exit code), then `caddy reload`.
3. Add the ingress rule through the API: `GET /accounts/<account>/cfd_tunnel/<tunnel-id>/configurations`, insert `{"hostname": "app.example.com", "service": "http://caddy"}` before the catch-all rule, `PUT` it back.
4. DNS: CNAME `app` → `<tunnel-id>.cfargotunnel.com`, proxied.
5. Check through the CDN: the page loads, the live version is the new one, and dynamic paths are not cached.

## launchd

**24. A scheduled job failed with `env: node: No such file or directory`.**
launchd gives jobs a bare `PATH` (`/usr/bin:/bin`), so Homebrew tools are missing. The manual test passed because it ran in an interactive shell. Now each wrapper starts with `export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"`, and we test it once with `env PATH=/usr/bin:/bin /bin/bash wrapper.sh`.

**25. Monitor jobs stopped running after a restart.**
`StartInterval` did not fire after a reboot (`runs = 0`). Now our monitor jobs use `StartCalendarInterval`.

## Monitoring and backups

**26. Backups failed for weeks without anyone noticing.**
Tailscale on the backup machine had logged out. Now SSH falls back to the LAN address when Tailscale is down (a `Match host ... exec` block in `~/.ssh/config`), and key expiry is disabled for that node.

**27. Every target was reported down at once.**
The monitor had lost its own Tailscale connection. Now it checks its own path first, repairs it once if it can, and otherwise sends one alert about itself.

**28. Jobs failed for weeks and nobody heard.**
Monitoring checked reachability, not results. Now every scheduled job and workflow has an error channel, and the monitor checks the exit status of launchd jobs. Alerts about normal things were removed: they teach you to ignore alerts.

**29. Restoring a dump into a scratch database overwrote production.**
A `mysqldump --databases` file starts with `USE <name>;`, which overrides the database on the command line. Now: `grep -E '^(USE|CREATE DATABASE)' dump.sql` before every import, strip those lines for a scratch restore, and dump the target database first.

## Updates

**30. We want security fixes automatically, and nothing that can break the server.**
Our layers: Apple security data, Rapid Security Responses and App Store apps (Tailscale) update automatically. macOS versions and Docker Desktop only notify; we pick the moment. Homebrew upgrades weekly and respects `brew pin`. Container images only change through a deploy. We deliberately leave `AutomaticallyInstallMacOSUpdates` off. A guard checks disk, container health, backup age and Tailscale before an update; a check five minutes after tests containers and a few sites.

## Make this better

This is what bit us. You probably run things differently, and better in places. Tell us what bit you and what you do differently: open an issue or a thread at https://github.com/RichardTheuws/ai-toolkit/discussions.

---

Written with Claude, checked by Richard.
