# Een Obsidian-vault als gedeeld geheugen van Claude Code

Het auto-geheugen van Claude Code sleutelt op de map waarin je een sessie start. Dat is goed voor feiten over één checkout. Het is niet goed voor kennis die hoort bij een project dat over meerdere repo's loopt, of bij al je werk tegelijk: waarom je X boven Y koos, wat er de vorige keer misging, wat waar vastzit.

Die tweede soort kennis houden wij bij in een gewone Obsidian-vault: Markdown-bestanden in een Git-repo. Claude leest eruit bij de start van een sessie en schrijft erin via een paar commando's. Scripts houden de overzichtsnotities bij. Dezelfde bestanden openen we in Obsidian om te lezen, te linken en na te denken.

Dit draaiboek beschrijft het patroon. De vault-scripts zelf zijn nog niet gepubliceerd; dat is wel de bedoeling. De twee commando's en de lekpoort die hieronder voorkomen, staan in deze repo.

## Het idee erachter

Andrej Karpathy beschreef dit als een [LLM-wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f): in plaats van bij elke vraag opnieuw uit ruwe bronnen te zoeken, laat je het model een blijvende wiki opbouwen en onderhouden die met de tijd groeit. De mens cureert en vraagt; het model doet de boekhouding (kruisverwijzingen, samenvattingen, controles).

Hij werkt met drie lagen, en wij ook:

- **Ruwe bronnen**, die de agents nooit aanpassen: het auto-geheugen van Claude, de git-geschiedenis, documenten die je erin zet, je eigen prompts.
- **De wiki**: de vault zelf.
- **Het schema**: één document dat elke agent en elke sessie vertelt waar iets hoort en welke frontmatter elk notitietype nodig heeft. Alleen de mens past het aan. Een agent die zijn eigen regels kan herschrijven, draait in een kringetje.

Onze belangrijkste aanpassing: wij werken over veel projecten, niet over één onderwerp. Daarom kwamen er een projectnotitie bij, een grens op hoeveel pagina's één ingest mag raken (vijf), en meerdere controlescripts in plaats van één.

## Indeling: PARA plus twee

```text
~/vault/
  00-Inbox/        snel vastleggen, later sorteren
  01-Projects/     één notitie per actief project
  02-Areas/        doorlopende verantwoordelijkheden zonder einddatum
  03-Resources/    decisions/, learnings/, patterns/, naslag
  04-Archive/      afgerond of slapend werk (agents verplaatsen hier alleen naartoe)
  05-Daily/        één notitie per dag
  _meta/           schema, overzichtsnotities (MOC's), gegenereerde indexen
  _templates/      één sjabloon per notitietype
  Memory/          alleen-lezen spiegel van Claudes auto-geheugen
```

PARA (Projects, Areas, Resources, Archive) is de methode van Tiago Forte. Inbox en Daily zijn de twee toevoegingen. Elk notitietype heeft precies één thuismap; een notitie in de verkeerde map is een fout in de controle.

## Eén projectnotitie per repo

Elk project krijgt een notitie in `01-Projects/` met frontmatter die hem aan de code koppelt:

```yaml
---
type: project
status: active
priority: medium
tech: [nextjs, postgres]
repo: ~/code/acme-shop
created: 2026-03-02T09:00:00Z
tags: [project/active]
---
```

Het veld `repo:` maakt de vault projectbewust. Een SessionStart-hook kijkt naar de huidige werkmap, zoekt de projectnotitie waarvan `repo:` overeenkomt, en zet die in de sessie, samen met de dagnotitie van vandaag en de open blokkades. Hij heeft een budget van 200 ms en waarschuwt alleen: ontbreekt de vault, dan start de sessie gewoon.

Zet oude namen van een project in `aliases:`, zodat een beslissing onder de oude naam toch bij het juiste project terechtkomt.

## Beslissingen en lessen, gedateerd en getypeerd

Twee soorten notities dragen het meeste:

- **Beslissingen** (ADR's, naar Michael Nygard): context, beslissing, overwogen alternatieven, gevolgen, status (`proposed`, `accepted`, `superseded`, `deprecated`).
- **Lessen**: wat er gebeurde, wat we leerden, de oorzaak, hoe je het toepast. Getypeerd als `gotcha`, `success`, `failure` of `anti-pattern`.

Beide staan in `03-Resources/`, met datum en titel in de naam (`2026-03-14-idempotency-key-is-het-order-id.md`), een veld `project:` en een link terug naar de projectnotitie. We schrijven ze met `/decision <project> "<titel>"` en `/learning <project> "<titel>"`. Beide commando's staan in [`commands/`](../../commands/). De sjablonen zijn er als handmatige terugval.

Duikt dezelfde les op in drie of meer projecten, dan wordt het een kandidaat-patroon in `03-Resources/patterns/`. Een wekelijks script stelt die voor; een mens keurt ze goed.

## Overzichtsnotities die zichzelf opbouwen

Sommige notities zijn pure weergaven: waar we deze week aan werkten (uit de git-activiteit per `repo:`), wat er over projecten heen vastzit, hoe notities naar elkaar linken, kapotte links en wezen. Geplande scripts bouwen ze bij elke run opnieuw op. Ze zijn idempotent en schrijven atomair.

Elke weergave begint met een banner:

```markdown
_Gemaakt door focus-monitor op 2026-03-14T06:00:00Z. Niet met de hand bewerken; wordt bij elke run overschreven._
```

Die banner doet ertoe. Zonder banner voegt iemand een nuttige regel toe, wist de volgende run hem, en zakt het vertrouwen in het hele systeem. Zet je eigen gedachten in een gewone notitie en link naar de weergave.

## Een spiegel van Claudes geheugen, één kant op

Een klein script kopieert `~/.claude/projects/*/memory/` naar `Memory/` in de vault, één map per project. Het draait vanuit een hook na elke geheugenschrijfactie, met een geplande terugval. Het werkt één kant op: niets in de vault schrijft terug, en agents behandelen `Memory/` als alleen-lezen.

Waarom: zo is het auto-geheugen van alle projecten op één plek doorzoekbaar en te linken, zonder dat de vault er een tweede bron van waarheid voor wordt. Wat in het auto-geheugen zelf hoort, staat in het [draaiboek geheugenhygiëne](geheugenhygiene.md).

## Synchroniseren via Git, niet via iCloud

De vault is een besloten Git-repo. De Obsidian Git-plugin commit en pusht op een timer. iCloud houden we er bewust buiten: scripts en Obsidian die dezelfde bestanden schrijven terwijl een cloudsync loopt, is vragen om race-condities en conflictkopieën. Git geeft geschiedenis, diffs, en een duidelijk antwoord als twee schrijvers het oneens zijn.

## Het blok "Stand": het model schrijft, het script bewaakt

Elke projectnotitie heeft een blok met de huidige stand: waar het staat, wat geldt (met bij elke regel een link naar de beslissing erachter), lessen die nog gelden, en wat openstaat.

Die samenvatting schrijven vraagt oordeel, dus het model schrijft hem. Alles wat niet van oordeel mag afhangen, doet een script:

1. Het levert het model de bronnen aan: beslissingen, lessen en open acties van het project, met wat nieuw is sinds de vorige keer gemarkeerd.
2. Het controleert wat terugkomt: de vier vaste koppen, een maximum aantal regels, een bronlink bij elke regel onder "Wat geldt" en "Lessen", en geen vervallen beslissing die wordt aangehaald alsof ze nog geldt.
3. Het schrijft het blok tussen twee markeringen, atomair (tijdelijk bestand, dan hernoemen), en raakt niets buiten de markeringen.
4. Het bewaart een controlesom van het blok in de frontmatter. Klopt het blok op schijf daar niet meer mee, dan heeft iemand erin getypt; het script verplaatst die tekst naar een sectie "handmatige aantekeningen" in plaats van hem weg te gooien.
5. Een dagelijkse controle noemt elk project waarvan de bronnen nieuwer zijn dan het blok.

```markdown
<!-- stand:begin (beheerd; niet met de hand bewerken) -->
## Stand
### Waar het nu staat
### Wat geldt
### Lessen die nog gelden
### Openstaand
<!-- stand:end -->
```

Het model schrijft, het script bewaakt. Die verdeling werkt op de meeste plekken waar een LLM schrijft in een bestand waar andere gereedschappen op leunen.

## Dossiers: een deel van een privévault delen

Soms moet iemand anders een deel zien van wat je weet, bijvoorbeeld een klant die de beslissingen over zijn project wil kunnen lezen. De vault zelf geven is uitgesloten. Wat we in plaats daarvan doen:

- **Per notitie aanzetten.** Alleen notities met `share: [doelgroep]` in de frontmatter gaan mee in het dossier van die doelgroep. Standaard wordt niets gedeeld.
- **Een afgeleide map**, gebouwd uit een klein beschrijvingsbestand per doelgroep. De bouw pusht nooit uit zichzelf naar een remote, en weigert een doelmap te overschrijven die met de hand is aangepast.
- **Een poort die bij één treffer de hele export weigert.** Voordat er iets geschreven wordt, gaat elke pagina langs controles op bedragen en prijswoorden, IP-adressen en mailadressen, vormen van sleutels, interne links en thuispaden, namen buiten een toegestane lijst, en alles uit privémappen (dagnotities, de map met personen, de geheugenspiegel, het gedeelte van onze persoonlijke assistent). Eén treffer, en er wordt niets geschreven.

De eerste poging leerde ons de rest. Notities die op titel voor delen waren voorgesteld, leken in orde en de poort was groen, maar een losse controle over de gebouwde map vond toch adressen, cijfers en namen van configbestanden. Een titel zegt niet wat er in de tekst staat, en een groene poort bewijst alleen dat haar eigen regels niets vonden. Dus: lees elke notitie op inhoud voordat je hem deelbaar maakt, reken erop dat de meeste een eigen deelbare tekst nodig hebben, draai na elke bouw een onafhankelijke nacontrole, en maak van elke vondst een nieuwe regel in de poort, met een geplant lek in de testset.

De [lekpoort](../../scripts/leak-gate/) in deze repo werkt volgens hetzelfde idee, voor een map die je op het punt staat te publiceren.

## Beginnen

Je hebt dit niet allemaal op dag één nodig. Een bruikbare volgorde:

1. Een vault in Git met de PARA-mappen en een korte schemanotitie.
2. Projectnotities met `repo:`, en een SessionStart-hook die de juiste laadt.
3. `/decision` en `/learning`.
4. Eén gegenereerde weergave (bijvoorbeeld de activiteit van deze week) met de banner.
5. De geheugenspiegel, het blok Stand en dossiers, zodra je er behoefte aan hebt.

## Maak dit beter

Dit is hoe wij nu werken, geen standaard. Werk je anders met een vault en Claude Code, of vond je waar dit breekt? Open een issue of begin een discussie op https://github.com/RichardTheuws/ai-toolkit/discussions.

---

*Geschreven met Claude, nagelopen door Richard.*
