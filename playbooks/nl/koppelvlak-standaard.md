# Een koppelvlak-standaard voor je eigen systemen

Draai je meer dan een handvol kleine apps, dan gaan de naden ertussen stuk. Niet de apps zelf, maar de plekken waar de ene app iets aan de andere doorgeeft.

Dat leerden we op één dag, toen we vier keer dezelfde soort naad repareerden, in vier repo's:

| Waar | Wat er misging |
|---|---|
| De boekhoudapp | Die koppelde binnenkomende aanvragen op mailadres en ontdubbelde niet op de id van de afzender. Leverde het intakeformulier twee keer, dan kwamen er dubbele notities en dubbele meldingen. |
| Monitoring | Het intakeformulier telde mislukte taken in zijn health-endpoint. Niets keek ooit naar dat getal. |
| Het CRM en het intakeformulier | Twee vocabulaires en twee tokenstelsels voor hetzelfde dashboard. |
| Het intakeformulier en onze assistent | Het formulier kon een melding sturen, maar antwoorden kon niet, want de admin-API zat achter een browsercookie. |

Vier symptomen, één oorzaak: elk systeem loste de naad opnieuw zelf op. Dus schreven we het één keer op. Elke nieuwe naadbug wordt nu een regel in dit document, niet alleen een fix in één repo.

## De vijf regels

### 1. Server-naar-server: een geheim in een header, en uit als het geheim ontbreekt

Tussen onze eigen diensten volstaat een gedeeld geheim in een header, vergeleken in constante tijd. Nooit een browsercookie voor verkeer tussen machines.

De belangrijke helft: **is het geheim niet ingesteld, dan weigert het endpoint met 503.** Een verkeerd ingerichte omgeving mag nooit stilletjes gegevens aannemen. We kwamen uit op één kleine helper met drie uitkomsten: ok, 401 (verkeerd geheim), 503 (geen geheim ingesteld). Die helper is onze referentie, niet een losse route.

Op het open internet (betaalproviders, chatplatforms, externe partijen) gebruiken we in plaats daarvan **HMAC-ondertekening over de payload**. Dan is ook de inhoud meegetekend, en is een uitgelekt geheim alleen niet genoeg. We schreven de standaard eerst met alleen de header-variant, en pasten hem aan toen een van onze eigen projecten het beter bleek te doen.

### 2. Elke ingest is idempotent op `(source, source_ref)`

`source` is het verzendende systeem. `source_ref` is de id van de gebeurtenis in dat systeem, bijvoorbeeld de id van een inzending. Met een unieke index op dat paar geeft een herhaalde levering hetzelfde antwoord, zonder tweede notitie, factuur of melding.

Dit is de keerzijde van regel 3. Wie minstens één keer levert, verplicht de ontvanger tot idempotentie. Maak die afspraak expliciet.

Eén les uit de fix: ontbrak de id, dan viel onze handler stil terug op de oude match op mailadres, zonder ontdubbeling. Onschuldig zolang de afzender altijd een id meestuurt, maar een stille terugval is een toekomstige bug. Maak hem luid.

### 3. Levering is minstens één keer, met een ladder en een zichtbaar restant

Een taak verlaat de wachtrij pas als hij gelukt is. Nieuwe pogingen volgen een ladder: 30 seconden, 1 minuut, 2 minuten enzovoort, tot een uur, acht pogingen. Daarna is de taak **zichtbaar mislukt**, niet weg. Liever dubbel dan gemist.

### 4. Wat mislukt is, wordt geteld en iemand kijkt ernaar

Een teller in `/api/health` is pas een vangnet als iets hem leest. Alarmeer op **mislukte taken > 0**, niet op HTTP 200: een app kan prima draaien terwijl de wachtrij vastzit. Eén monitor voor alle systemen, met een interval dat past bij wat een gemiste taak kost. Een gemiste klantaanvraag willen we binnen het uur weten, niet de volgende dag.

### 5. Eén kanaal voor aandacht, in beide richtingen

Alles wat onze aandacht vraagt, gaat via één kanaal (bij ons: onze persoonlijke assistent in Telegram), in dezelfde vorm: een gebeurtenis, een bericht met knoppen, en een **terugweg**. Een antwoord via tik, tekst of spraak wordt een antwoord in het bronsysteem. Faalt de terugweg, dan zegt het kanaal dat. Nooit stil falen, anders denk je dat je geantwoord hebt terwijl dat niet zo is.

Mail is de terugval, niet het hoofdkanaal.

Een verfijning voor producten die bij meerdere klanten draaien: het kanaal is een eigenschap van de *instance*, niet van de code. Onze eigen instance meldt aan onze assistent. De instance van een klant houdt het eigen kanaal van die klant. Anders lopen de meldingen van elke klant over onze telefoon.

### En: één dienst per capaciteit

Twee exemplaren van dezelfde capaciteit op één server (bijvoorbeeld twee installaties voor spraak-naar-tekst) mogen, maar dan als besluit met een opgeschreven reden. De standaard is één dienst per capaciteit.

## Checklist voor een nieuwe naad

- [ ] Geheim in een header, vergelijking in constante tijd, 503 als de omgevingsvariabele ontbreekt
- [ ] HMAC over de payload als het endpoint vanaf internet bereikbaar is
- [ ] Uniek `(source, source_ref)`; een herhaling geeft hetzelfde resultaat met `duplicate: true`
- [ ] Geen stille terugval als `source_ref` ontbreekt
- [ ] De afzender gebruikt een outbox met een ladder; mislukte taken blijven zichtbaar
- [ ] Aantal mislukte taken in het health-endpoint, en een monitor die alarmeert bij > 0
- [ ] Meldingen gaan via het ene kanaal, met een werkende terugweg
- [ ] Elke actie aan de ontvangende kant is idempotent, ook "opgelost" en "archiveren"

## Een minimale schets

Een idempotente webhook-ontvanger in Python met FastAPI en SQLite. Hij laat regels 1 en 2 zien; de outbox van de afzender regelt regel 3.

```python
import hmac, os, sqlite3, json
from fastapi import FastAPI, Header, HTTPException, Request

app = FastAPI()
db = sqlite3.connect("ingest.db", check_same_thread=False)
db.execute("""CREATE TABLE IF NOT EXISTS ingests (
  source TEXT NOT NULL, source_ref TEXT NOT NULL,
  result TEXT NOT NULL, PRIMARY KEY (source, source_ref))""")

def check_secret(given: str | None) -> None:
    expected = os.environ.get("INGEST_SECRET")
    if not expected:
        raise HTTPException(503, "ingest uit: geen geheim ingesteld")
    if not given or not hmac.compare_digest(given, expected):
        raise HTTPException(401, "verkeerd geheim")

@app.post("/api/ingest")
async def ingest(request: Request, x_ingest_secret: str | None = Header(None)):
    check_secret(x_ingest_secret)
    body = await request.json()
    source, ref = body.get("source"), body.get("id")
    if not source or not ref:
        raise HTTPException(422, "source en id zijn verplicht")  # luid, geen terugval

    row = db.execute("SELECT result FROM ingests WHERE source=? AND source_ref=?",
                     (source, ref)).fetchone()
    if row:
        return {**json.loads(row[0]), "duplicate": True}

    result = {"customer_id": create_note_and_notify(body)}  # jouw bijwerking
    try:
        db.execute("INSERT INTO ingests VALUES (?,?,?)", (source, ref, json.dumps(result)))
        db.commit()
    except sqlite3.IntegrityError:  # een parallelle levering was eerder
        row = db.execute("SELECT result FROM ingests WHERE source=? AND source_ref=?",
                         (source, ref)).fetchone()
        return {**json.loads(row[0]), "duplicate": True}
    return {**result, "duplicate": False}
```

Leg in productie de rij `(source, source_ref)` vast *vóór* de bijwerking (of doe beide in één transactie), zodat twee parallelle leveringen niet allebei een melding sturen. De schets houdt het kort.

## Toegepast: één route voor feedback van gebruikers naar de backlog

We ontdekten dat vijf van onze apps elk een eigen feedbackknop hadden. Elk met een eigen opslag en een eigen bot. Geen enkele kwam uit in onze backlog, en bij geen enkele hoorde de gebruiker ooit dat zijn melding was opgelost. De feedback-standaard maakt daar één route van, gebouwd op de vijf regels hierboven.

1. **Vastleggen in de bron.** De database van de app is de bron. Vier soorten: fout, vraag, idee en check-in. De context (pagina, versie, rol) gaat automatisch mee. Meldingen zijn afgeschermd per organisatie.
2. **Melden via het ene kanaal.** De app stuurt een `feedback`-gebeurtenis vanuit een eigen outbox met een ladder. Bij een vraag stuurt hij een conceptantwoord mee. Tekst die naar het model of het chatplatform gaat, bevat geen contactgegevens: de persoon is een pseudoniem. Ook links en tekenreeksen die op een token lijken gaan eruit, want wie een privélink plakt, plakt een sleutel.
3. **Beslissen met één tik.** Knoppen: Verstuur, Aanpassen, Oppakken, Archiveren. **Een antwoord aan een gebruiker gaat pas weg na een tik van een mens.** Onder elk antwoord staat dat het met AI is opgesteld.
4. **De backlog in.** Alleen wat we oppakken wordt een dev-actie in onze notitie-repo, met `source: feedback` en `source_ref: <app>:<id>`. In het [draaiboek persoonlijke assistent](persoonlijke-assistent.md) staat hoe die acties bij Claude Code komen.
5. **De cirkel sluiten.** Elke 15 minuten kijkt de assistent welke feedback-acties op `done` staan en stuurt `resolved` naar de app. De app zet de melding op opgelost en mailt de gebruiker één keer.

De terugweg van de assistent naar de app is per app één idempotent endpoint met een veld `action` (`answer`, `picked_up`, `archive`, `resolved`) en een eigen geheim in de header. Een 404 telt als afgehandeld.

Een nieuwe app aansluiten is: een tabel en een outbox in die app, één configuratieregel bij de assistent, een projectnotitie zodat de sessiestart de acties vindt, en een alinea in de privacyverklaring over wie het antwoord opstelt en hoe lang meldingen bewaard blijven.

Lessen uit de eerste bouw:

- **Bezorg meldingen in een eigen, snelle tik.** Meeliften op een cron van 5 minuten betekende dat een melding er pas na 4 tot 6 minuten was. Een aparte tik van 30 seconden bracht dat terug tot ongeveer een halve minuut. Draai nooit twee bezorgers naast elkaar, anders komen berichten dubbel binnen.
- **Zet configuratiewaarden met komma's tussen aanhalingstekens.** Eén regel zonder werd overgeslagen, met alleen een melding in de foutlog; de melding kwam wel in de chat, maar zonder knoppen.
- **Houd de knopdata klein.** Telegram begrenst callback-data op 64 bytes, dus houden we bronnamen kort.

## Maak dit beter

Deze regels komen uit onze eigen bugs, dus ze dekken onze blinde vlekken alleen voor zover we ertegenaan zijn gelopen. Heb je een naadregel die we missen, of een nettere manier voor een van deze, open dan een issue of begin een gesprek op https://github.com/RichardTheuws/ai-toolkit/discussions.

---

*Geschreven met Claude, nagelopen door Richard.*
