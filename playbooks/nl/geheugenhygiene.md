# Geheugenhygiëne voor het auto-geheugen van Claude Code

Claude Code houdt per project een auto-geheugen bij: een index `MEMORY.md` plus kleine onderwerpbestanden in `~/.claude/projects/<project>/memory/`. De index wordt aan het begin van elke sessie in de context gelezen. De onderwerpbestanden worden pas geopend als de index ernaar wijst en de taak erom lijkt te vragen.

Dat verschil is de kern van dit draaiboek. De index kost je elke sessie context. De onderwerpbestanden zijn bijna gratis tot ze gebruikt worden. Zonder discipline groeit de index, gaat hij sessienotities en implementatiedetails bevatten, en betaalt elke sessie voor alles.

Dit is wat bij ons werkt. Het is niet de enige manier. Laat ons weten wat jij anders zou doen.

## De regels in het kort

1. **De index bevat verwijzingen, geen inhoud.** Elke regel beantwoordt één vraag: "waar vind ik X?"
2. **Eén feit per bestand.** Een onderwerpbestand gaat over één ding en is op zichzelf te lezen.
3. **Geen sessielogboek in het geheugen.** Git en je sessiegereedschap weten al wat er wanneer gebeurde.
4. **Geen versiestempels in koppen.** `## Betalingen (v2.3, maart)` is een changelog-fragment in vermomming.
5. **In een monorepo: een router plus één index per werkstroom.**
6. **Slapende werkstromen naar het archief.** Uit de index, niet weggegooid.
7. **Meet wat context kost, niet wat makkelijk te tellen is.**

## 1. De index is een kaart

Wat in `MEMORY.md` hoort:

- Vaste feiten die je elke sessie nodig hebt (huidige versie, hoofdpaden, deploy-doel), hooguit een paar regels.
- Eén regel per onderwerpbestand, met een haakje dat zegt wat dat bestand onderscheidt.
- Een verwijzing naar het geheugen van een ander project, als dat elke sessie telt.

Wat er niet in hoort:

- Uitleg langer dan één regel.
- Lijsten met implementatiedetails (poorten, scriptnamen, configpaden).
- Versiegeschiedenis en changelog-fragmenten.
- Handleidingen en architectuurbeschrijvingen.
- Secties als "Laatste sessie" of "Volgende sessie".

Een snelle toets voordat een regel in de index komt: begrijpt een toekomstige sessie deze regel zonder de rest van het project te kennen? Zo niet, dan hoort hij in een onderwerpbestand.

### Vorm van een indexregel

```markdown
- [Checkout-valkuilen](feedback_checkout_gotchas.md) — webhook-retries boeken dubbel; idempotency-key is het order-id
```

Eén regel, hooguit zo'n 150 tekens. Het haakje na het streepje noemt het detail dat dít bestand het juiste maakt. Vermijd haakjes als "bevat notities over checkout" of "belangrijke lessen". Laat datums en statuswoorden weg; die staan in het bestand.

Houd de koppen plat en weinig. Wij gebruiken er vijf: actieve projecten, lessen en anti-patronen, technische naslag, voorkeuren van de gebruiker, en een kort blok vaste projectfeiten. Een losse kop voor één onderwerp ("## Betaaldienst") is een teken dat dat onderwerp een eigen bestand wil.

## 2. Eén feit per bestand

Bestandsnamen beginnen met een van vier voorvoegsels:

| Voorvoegsel | Bevat | Leeft tot |
|---|---|---|
| `feedback_` | Lessen, anti-patronen, "doe dit niet" | Altijd |
| `project_` | Stand en beslissingen van een stuk werk | Het werk gearchiveerd is |
| `reference_` | Vaste technische naslag | De bron verandert |
| `user_` | Voorkeuren en communicatiestijl | Altijd |

Na het voorvoegsel: snake_case, hooguit vier woorden, specifiek genoeg dat de naam de inhoud aankondigt. `project_notes.md` zegt niets. `project_checkout_v2.md` is ook fout: versies staan in het bestand, niet in de naam.

Elk bestand begint met frontmatter:

```yaml
---
name: Checkout-valkuilen
description: Webhook-retries boeken orders dubbel; gebruik het order-id als idempotency-key
type: feedback
---
```

De `description` is de zoeksleutel. Schrijf hem zo dat het antwoord op "is dit relevant voor wat ik nu doe?" altijd ja of nee is, nooit misschien. Noem het onderwerp, niet de aanleiding.

Voeg kleine bestanden niet samen om het aantal omlaag te krijgen. In een opslag die bestanden lui laadt, zijn veel kleine bestanden met een scherpe omschrijving juist een voordeel. Voeg alleen samen als twee bestanden over hetzelfde gaan.

## 3. Geen sessielogboek in het geheugen

Een sectie "Laatste sessie" groeit elke sessie: datum, samenvatting, vervolgstappen, blokkades. Na een paar maanden is het het grootste deel van de index, en vrijwel niets ervan klopt nog.

Waar die informatie al staat:

- Wanneer de laatste sessie was: in je sessiegereedschap of hook-log.
- Wat er sindsdien veranderde: `git log --since=<laatste sessie>`.
- Wat er besloten is: in commitberichten, of in een `project_*.md` als de beslissing groter is dan een commitbericht.
- Open punten van lopend werk: onder "Open punten" in het bestand van dat project.

Het geheugen is voor wat waar blijft. Een startcommando voor de sessie kan de rest uit deze bronnen opbouwen.

## 4. Router plus werkstroom-indexen (monorepo's)

Claude Code sleutelt het geheugen op de **map** waarin je de sessie start. Kennis hoort echter bij een **project**, en een project loopt vaak over meerdere mappen of repo's. Die twee assen lopen niet gelijk.

Dat leerden we de harde weg. Eén repo bevatte vijf losse werkstromen. De voor de hand liggende oplossing, "geef elke werkstroom een eigen geheugen door sessies in de submap te starten", was al half gedaan. Dat bleek de oorzaak van de rommel, niet de oplossing: een rij submap-geheugens met elk één bestand, en welk geheugen je kreeg hing af van waar je toevallig startte. Verder splitsen langs de map-as maakte het erger.

Wat wel werkte: één geheugen voor de repo houden en splitsen op **hoe je de kennis nodig hebt**:

- `MEMORY.md` wordt een **router** van zo'n 30 regels: per werkstroom één regel naar een eigen `INDEX-<werkstroom>.md`, plus de paar regels die overal gelden.
- Elke werkstroom-index wijst naar zijn eigen onderwerpbestanden.
- Een sessie laadt de router en één index. Onderwerpbestanden komen pas mee als ze relevant zijn.
- Submap-geheugens blijven dun: de harde feiten van die checkout (paden, stack, deploy-eigenaardigheden) plus een verwijzing omhoog.

Het resultaat bij ons: de vaste context per sessie ging van ongeveer 15 KB naar ongeveer 2 KB voor alleen de router, en ongeveer 5 KB voor een sessie in de drukste werkstroom.

Eén kanttekening. Kennis uit het geheugen verhuizen (bijvoorbeeld naar een notitie-vault) kost automatische herinnering. Geheugenbestanden worden gevonden via hun omschrijving; andere notities moet je bewust lezen. Voor beslissingen en geschiedenis is dat prima. Feiten die je nooit fout mag hebben, blijven in het geheugen.

## 5. Slapende werkstromen naar het archief

Een werkstroom zonder activiteit in weken hoeft niet elke sessie mee te laden. Zet de bestanden in `memory/archive/`, laat de frontmatter staan, voeg een datum `archived:` toe en haal de regel uit de router. Zet een korte README in de archiefmap die zegt hoe je hem terughaalt.

Activiteit is niet altijd commits. Een van onze werkstromen levert bijna geen commits op en is toch volop in gebruik; een commit-teller zou hem slapend noemen. Beslis per werkstroom, niet op een getal.

## 6. Meet wat context kost

We hadden een audit die rood werd bij meer dan 30 geheugenbestanden. Na de overstap op een router daalden de vaste kosten per sessie met zo'n 80 procent, en de audit werd *slechter*: vijf index-bestanden erbij. Hij meldde ook een hele rij "weeskinderen" zonder indexregel, terwijl een dekkingscontrole er geen vond. Ze waren allemaal geïndexeerd, één niveau lager.

Een alarm dat altijd afgaat, is geen alarm. De oplossing was niet de drempel ophogen tot het stil werd, maar meten wat pijn doet:

- **Meet de index, niet de voorraad.** Wat elke sessie laadt, is de kostenpost. Meet bij een router de grootste index, niet het totale aantal bestanden. Het totaal blijft alleen als vangnet.
- **Volg de index één niveau diep.** Een bestand telt als geïndexeerd als `MEMORY.md` het noemt, of als een bestand dat `MEMORY.md` noemt het noemt.
- **Houd de signalen die echte rommel vangen:** verouderde sessiebestanden, versiestempels in koppen, lange secties in de index zelf.

De drempels die wij voor de index gebruiken: groen onder de 80 regels, oranje van 80 tot 150, rood boven de 150. Voor onderwerpbestanden: lessen blijven kort (een les is geen verhaal), naslagbestanden mogen langer.

## Het gereedschap

Deze repo heeft een auditscript in [`scripts/memory-audit/`](../../scripts/memory-audit/). Het leest het geheugen van een project, geeft groen, oranje of rood, en noemt concrete acties. Het kent de router-opzet hierboven. Zie de README voor het gebruik.

## Voor en na

Een verzonnen voorbeeld. Voor: een `MEMORY.md` voor een repo met een webshop, een nieuwsbrief en wat interne tools.

```markdown
# acme-shop memory

## Laatste sessie (14 maart)
- Aan checkout-webhooks gewerkt, half af
- Volgende: refunds testen, btw-regels navragen
- Geblokkeerd op sandbox-sleutels van de betaaldienst

## Betalingen (v2.3, maart)
- Webhook-handler in src/payments/webhook.ts, 5x retry met backoff
- Idempotency-key = order-id, anders boeken retries dubbel
- Sandbox op poort 4010, live op 4000
- Refund-flow gebruikt nog de oude API, later migreren

## Nieuwsbrief
- Verstuurt via een queue-worker, cron om 06:00
- Template in templates/mail/, alleen tabellen, geen CSS-variabelen
- Afmeldlink moet absoluut zijn

## Patronen & valkuilen
- Docker-buildcache breekt bij een gewijzigde lockfile
- Draai het seed-script nooit tegen productie
- De CMS-preview negeert slashes aan het eind
[...]
```

Na: een router, met de details in eigen bestanden.

```markdown
# acme-shop memory (router)

Laad alleen de index van de werkstroom waar deze sessie over gaat.

| Werkstroom | Index |
|---|---|
| Shop en betalingen | [INDEX-shop.md](INDEX-shop.md) |
| Nieuwsbrief | [INDEX-nieuwsbrief.md](INDEX-nieuwsbrief.md) |
| Interne tools | slapend, zie archive/ |

## Geldt overal
- [Productieveiligheid](feedback_production_safety.md) — nooit seeden op productie; deploy alleen via het script
- [Docker-cache](feedback_docker_cache.md) — buildcache breekt bij nieuwe lockfile; bouw zonder cache
```

En `INDEX-shop.md`:

```markdown
- [Checkout-valkuilen](feedback_checkout_gotchas.md) — webhook-retries boeken dubbel; idempotency-key is het order-id
- [Betaalopzet](reference_payments_setup.md) — pad van de handler, poorten van sandbox en live
- [Refund-migratie](project_refund_migration.md) — oude API nog in gebruik; open punten in het bestand
```

Het blok "Laatste sessie" is weg; dat bewaren git en het sessielog. Het versiestempel is weg. Elk detail heeft één plek.

## Maak dit beter

Dit is hoe wij nu werken, geen standaard. Pak je het geheugen anders aan, heb je een betere drempel, of vond je een geval waarin dit advies misgaat? Open een issue of begin een discussie op https://github.com/RichardTheuws/ai-toolkit/discussions.

---

*Geschreven met Claude, nagelopen door Richard.*
