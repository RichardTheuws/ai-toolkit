# Apps van Claude draaien op een Mac mini

We draaien onze eigen apps en een reeks klantsites op een Mac mini thuis, het meeste geschreven met Claude Code. Hier staat wat er in productie misging, waarom, en hoe we het nu doen. De meeste punten kostten ons een storing of een avond voordat we ze opschreven.

**De opstelling.** Een Mac mini M4 draait alle containers onder Docker Desktop. Eén gedeelde Caddy-container is de reverse proxy voor elke site. Een Cloudflare-tunnel (een `cloudflared`-container) haalt het verkeer binnen, zodat de machine geen open poorten naar internet heeft. Een tweede, oudere Mac mini controleert de eerste elke 15 minuten en maakt 's nachts de back-up. Ze bereiken elkaar via Tailscale. Bestanden gaan daarnaast elke nacht versleuteld met restic buiten de deur.

Elk punt volgt dezelfde lijn: **wat je ziet**, **waardoor**, **wat we nu doen**.

## Uitrollen en rsync

**1. Een uitrol wiste bestanden die alleen op de server stonden.**
`rsync --delete` haalde een map met geheimen weg, en later de productie-`.env` met zijn reservekopieën. rsync spiegelt de bron. Wat niet in de repo staat, ziet hij als verwijderd, ook als het op de server thuishoort. Nu beschermen we wat alleen op de server hoort en tellen we eerst de verwijderingen in een proefrun:

```bash
rsync -rcn --delete --itemize-changes --filter='P .env*' ./ host:/srv/app/ > plan.txt
grep -c '^\*deleting' plan.txt   # moet 0 zijn, anders stoppen
```

**2. De uitsluitingen stonden in een shellvariabele, en geen ervan werkte.**
`EX="--exclude=.env* ..."; rsync $EX ...` werkt in bash. zsh splitst een niet-gequote variabele niet, dus rsync kreeg één onzinnig patroon en draaide `--delete` zonder één uitsluiting. Nu staan uitsluitingen letterlijk en gequote op de opdrachtregel, nooit in een variabele. De shell-guard in deze repo ([hooks/bash-guard/](../../hooks/bash-guard/)) komt uit punt 1 en 2: hij blokkeert `rsync --delete` naar een server zonder `.env`-bescherming, of met een variabele vol opties.

**3. rsync verving de productie-`docker-compose.yml` door die van development.**
De compose op de server wijkt bewust af (poorten, containernamen, extra diensten) en staat niet in git. Nu sluit elke rsync `docker-compose.yml`, `.env`, `.env.*` en datamappen uit. Een teruggezette compose controleren we door `docker compose -f <kandidaat> config --hash "*"` te vergelijken met het label `com.docker.compose.config-hash` van de draaiende containers. Alleen een gelijke hash betekent een exact herstel.

**4. De uitrol nam honderden MB's mee die niet in git zaten.**
Gerenderde video's en buildartefacten stonden wel op schijf, niet in git, en rsync nam ze mee. Een zelfgeschreven uitsluitlijst loopt altijd één vindplaats achter. Nu volgen we de ignore-regels van de repo zelf, met de uitsluiting van geheimen er expliciet bovenop: `--filter=':- .gitignore'`.

**5. Containers vielen na een uitrol om met `EACCES`.**
`rsync -a` houdt de eigenaar van de laptop aan. Die gebruiker bestaat niet in de container, en de bind-mount op macOS houdt dat strikt aan. Nu: `rsync --chown=<servergebruiker>:staff ...`, of een `chown -R` vóór de herstart.

**6. Een mislukte uitrol meldde exitcode 0.**
`./deploy.sh > log 2>&1; echo "EXIT=$?"` eindigt altijd met de exitcode van `echo`. Nu vangen we de code eerst op (`./deploy.sh; RC=$?`) en vertrouwen we nooit alleen op een exitcode: we vragen de draaiende app om zijn versie en vergelijken. De bash-guard blokkeert ook testen-en-dan-committen met een `;` ertussen.

## Docker op macOS

**7. De uitrol zei "Built" en "Started", maar de nieuwe route ontbrak.**
De build faalde in een vroege stap, en compose startte het vorige image onder dezelfde tag. Nu zoeken we in de bouwuitvoer naar `error|exit code` in plaats van de laatste regel te lezen, en controleren we dat de nieuwe inhoud echt in de container staat.

**8. Geheimen kwamen in een image terecht.**
Docker leest `.dockerignore`, nooit `.gitignore`. Met `COPY . .` en zonder `.dockerignore` ging de `.env` uit de buildmap het image in. Nu krijgt elke Dockerfile een `.dockerignore` met `.env`, `.env.*`, `!.env.example`, `.git` en `node_modules`, en controleren we het: `docker run --rm --entrypoint sh <image> -c "ls -la /app/.env"` moet zeggen dat het bestand niet bestaat.

**9. `docker build` via SSH liep vast op de sleutelhanger.**
De credential store van Docker Desktop wil een interactieve sessie om basisimages op te halen. Nu bouwen we op de laptop (ook arm64) en zetten we het image over: `docker save <img> | gzip | ssh host 'gunzip | docker load'`, dan `docker compose up -d --no-build`. Het vorige image taggen we eerst als terugval.

**10. Een config die op de host was aangepast, bleef in de container oud.**
Een bind-mount van één bestand blijft aan de oude inode hangen zodra het bestand vervangen wordt, en Docker Desktop cachet het. Caddy valideerde toen een afgekapt bestand. Nu mounten we de map, niet het bestand. Staat er al een bestandsmount, dan na de wijziging `docker restart` op de container.

**11. Postgres gaf fout 53100 terwijl de Mac ruim schijfruimte had.**
53100 is `disk_full`, en het gaat om de virtuele schijf van de Docker-VM, niet om die van macOS. Build-cache en oude volumes van alle projecten stapelen zich daar op. Nu: `docker system df` om te kijken, `docker builder prune -f` is veilig. Volumes alleen na controle, want daar staat data in.

**12. Containers bereiken geen broadcast of multicast op het thuisnetwerk.**
Docker Desktop draait in een VM achter NAT. Wake-on-LAN en zoeken via mDNS of SSDP komen er niet door; gewoon verkeer naar één adres wel. Nu wekken we apparaten via iets dat zelf op het netwerk zit, en zoeken we met vaste startadressen.

**13. Geen GPU in containers.**
Docker Desktop op macOS geeft Metal niet door, dus een model in een container draait op de CPU, 5 tot 10 keer trager. Nu draaien lokale modellen gewoon op macOS (Ollama uit Homebrew, gestart door een LaunchAgent), niet in Docker.

**14. Named volumes zaten niet in de back-up.**
Named volumes staan in de Docker-VM, en onze back-up neemt alleen mappen op de host mee. Nu staat de data van een app als bind-mount in een map die wel wordt meegenomen (`./var/<naam>:/data/<naam>`), en controleren we de back-up voordat we er iets over schrijven.

## Caddy

**15. Een rem per IP-adres gold voor alle bezoekers samen.**
Het verkeer loopt Cloudflare → cloudflared → Caddy → app. Caddy vertrouwde geen enkele proxy, dus elk verzoek leek van de cloudflared-container te komen. Nu staat `trusted_proxies` in Caddy voor het Docker-netwerk en geeft Caddy het bezoekersadres door uit `CF-Connecting-IP`. Apps lezen de eerste waarde van `X-Forwarded-For`, nooit het socketadres.

**16. Een kapotte Caddyfile werd toch herladen.**
`caddy validate | tail && caddy reload` test de exitcode van `tail`. Nu: back-up, valideren zonder pipe, exitcode controleren, dan herladen.

**17. Caddy importeerde regels uit een map waar een build in kon schrijven.**
Een kapot geïmporteerd bestand houdt na een herstart alle sites plat; een kwaadaardig bestand kan proxyregels toevoegen. Nu gaan gegenereerde regels via een validator naar de infra-repo, met een exact pad, nooit als glob uit een buildmap.

## Cloudflare-tunnel

**18. Een nieuwe ingress-regel in `config.yml` deed niets.**
Onze tunnel wordt op afstand beheerd. Het lokale bestand wordt genegeerd; de logregel `Updated to new configuration ... version=N` verraadt dat. Nu gaan ingress-wijzigingen via de API (zie het recept hieronder). Ze gelden direct, zonder herstart.

**19. `docker kill --signal=HUP cloudflared` legde alle sites plat.**
cloudflared ziet SIGHUP als afsluiten. Herladen zonder herstart bestaat niet. Nu: alleen `docker restart`.

**20. Bezoekers zagen om de paar uur een 502, terwijl de app gezond was.**
De log van cloudflared toonde `failed to sufficiently increase receive buffer size` en QUIC-timeouts. De UDP-buffer in de Docker-VM is te klein voor QUIC. Nu loopt de tunnel over HTTP/2: `tunnel --no-autoupdate --protocol http2 run`.

**21. `cloudflared tunnel route dns` maakte het verkeerde record.**
Bij een hostnaam buiten de zone van `cert.pem` plakt hij die zone erachter: `app.other.example` werd `app.other.example.example.com`. Nu gebruiken we `route dns` alleen voor de zone van het certificaat. Andere zones krijgen hun CNAME via de API, en we lezen de uitvoer van het commando.

**22. Een verse uitrol serveerde het oude JavaScript.**
Cloudflare cachet `.js` en `.css` standaard zo'n 4 uur aan de rand; HTML niet. Nu krijgen assets een hash of versie in de bestandsnaam (`app.3f9c1a2b.js`), waarnaar de ongecachte HTML verwijst. Voor video: `?v=3`. We controleren bij het CDN, niet bij de origin.

**23. Een pagina die nooit gecachet mocht worden, kwam terug als `HIT`.**
Cacheregels zijn geen firewallregels. Alle regels die matchen gelden, en per instelling wint de laatste. Nu staan uitzonderingen in de expressie van elke regel die cachet, en testen we elk pad met twee verzoeken: het eerste vult de cache, het tweede laat zien of hij pakt.

### Recept: een nieuw subdomein

1. Draai de app op hetzelfde Docker-netwerk als Caddy, of zet statische bestanden in de webroot.
2. Voeg een siteblok toe in Caddy, bijvoorbeeld `@app host app.example.com` met `handle @app { reverse_proxy mijnapp:<poort> }`. Maak een back-up van de Caddyfile, draai `caddy validate` (controleer de exitcode), dan `caddy reload`.
3. Zet de ingress-regel via de API: `GET /accounts/<account>/cfd_tunnel/<tunnel-id>/configurations`, voeg `{"hostname": "app.example.com", "service": "http://caddy"}` in vóór de vangnetregel, en `PUT` hem terug.
4. DNS: CNAME `app` → `<tunnel-id>.cfargotunnel.com`, via de proxy.
5. Controleer via het CDN: de pagina laadt, de draaiende versie is de nieuwe, en dynamische paden worden niet gecachet.

## launchd

**24. Een geplande taak faalde met `env: node: No such file or directory`.**
launchd geeft taken een kaal `PATH` (`/usr/bin:/bin`), dus Homebrew-tools ontbreken. De handmatige test slaagde omdat die in een interactieve shell draaide. Nu begint elk wrapperscript met `export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"`, en testen we het één keer met `env PATH=/usr/bin:/bin /bin/bash wrapper.sh`.

**25. De monitortaken draaiden niet meer na een herstart.**
`StartInterval` vuurde na een reboot niet (`runs = 0`). Nu gebruiken onze monitortaken `StartCalendarInterval`.

## Bewaking en back-ups

**26. Back-ups faalden wekenlang zonder dat iemand het merkte.**
Tailscale op de back-upmachine was uitgelogd. Nu valt SSH terug op het adres in het thuisnetwerk als Tailscale weg is (een `Match host ... exec`-blok in `~/.ssh/config`), en staat het verlopen van de sleutel uit voor die machine.

**27. Alle doelen werden tegelijk als storing gemeld.**
De monitor was zijn eigen Tailscale-verbinding kwijt. Nu controleert hij eerst zijn eigen pad, herstelt dat zo mogelijk één keer, en meldt anders één keer zijn eigen storing.

**28. Taken faalden wekenlang en niemand hoorde het.**
De bewaking keek naar bereikbaarheid, niet naar uitkomst. Nu heeft elke geplande taak en workflow een kanaal voor fouten, en controleert de monitor de exitstatus van launchd-taken. Meldingen over normale dingen zijn eruit: daarvan leer je meldingen negeren.

**29. Een dump terugzetten in een testdatabase overschreef productie.**
Een bestand van `mysqldump --databases` begint met `USE <naam>;`, en dat wint van de database op de opdrachtregel. Nu: vóór elke import `grep -E '^(USE|CREATE DATABASE)' dump.sql`, die regels weghalen bij een testherstel, en eerst een verse dump van de doeldatabase.

## Updates

**30. We willen beveiligingsupdates automatisch, en niets wat de server kan breken.**
Onze lagen: beveiligingsdata van Apple, Rapid Security Responses en App Store-apps (Tailscale) gaan automatisch. macOS-versies en Docker Desktop geven alleen een melding; wij kiezen het moment. Homebrew werkt wekelijks bij en respecteert `brew pin`. Container-images veranderen alleen via een uitrol. `AutomaticallyInstallMacOSUpdates` laten we bewust uit. Vóór een update controleert een guard schijfruimte, containers, de leeftijd van de back-up en Tailscale; vijf minuten erna test een controle de containers en een paar sites.

## Maak dit beter

Dit is wat ons beet. Jij doet het waarschijnlijk anders, en op punten beter. Vertel ons wat jou beet en wat je anders doet: open een issue of een draad op https://github.com/RichardTheuws/ai-toolkit/discussions.

---

Geschreven met Claude, nagelopen door Richard.
