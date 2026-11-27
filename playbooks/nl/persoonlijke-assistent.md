# Een persoonlijke assistent die werk doorgeeft aan een coding agent

Dit draaiboek beschrijft twee dingen die we elke dag gebruiken:

1. **Onze persoonlijke assistent**: een kleine dienst op een machine die thuis altijd aan staat, en waarmee we via Telegram praten. Hij leest mail, maakt conceptantwoorden, zet spraakmemo's om in tekst en kent onze notities.
2. **De lus van dev-acties**: hoe die assistent een codewijziging doorgeeft aan Claude Code, zonder zelf ooit code aan te raken.

De code van de assistent publiceren we niet. Die hangt aan het leven en werk van één persoon, en het meeste is lijm naar privé-accounts. De architectuur is het bruikbare deel, dus die delen we. Neem wat past, en vertel ons wat je anders zou doen.

## Deel 1: de architectuur

### Eén dienst, meerdere ingangen

De kern is één Python-dienst: FastAPI met de Claude Agent SDK, als achtergronddienst die zichzelf herstart. Er zijn maar een paar endpoints, vooral `POST /ask` en `POST /transcribe` voor spraak. De dienst luistert alleen op localhost en is alleen bereikbaar via een privénetwerk (een mesh-VPN), met daarbovenop een gedeeld geheim in een header. Er staan geen poorten open naar internet.

We kozen de Agent SDK in plaats van een kale completion-aanroep omdat de assistent een agent met tools is, en een warm proces antwoordt binnen seconden.

Telegram is de belangrijkste ingang. Een spraakingang op de desktop praat met dezelfde dienst. **Eén vast kanaal** is bij ons een regel: vraagt iets nieuws onze aandacht, dan breiden we de ene assistent uit. We bouwen er nooit een tweede bot naast.

### Telegram: long polling, geen webhook

De Telegram-bot draait als achtergrondtaak in de dienst zelf. Bij het opstarten roept hij `deleteWebhook` aan en daarna pollt hij `getUpdates`, voor berichten en voor tikken op knoppen.

Polling en webhooks sluiten elkaar uit bij Telegram. Roept iets `setWebhook` aan op dezelfde bot-token, dan stopt de polling en valt het hele kanaal stil. Dat hebben we bijna gedaan: we stonden op het punt een automatiseringsflow met een Telegram-webhook aan te zetten voor een nieuwe melding. Die had de assistent gebroken en iets gedupliceerd wat hij al kon. Het gebeurde omdat de assistent alleen op de server bestond en vanuit geen enkele repo te vinden was. Sindsdien heeft hij een referentienotitie die elk project kan vinden.

Nog twee regels uit dezelfde hoek:

- Draai nooit twee pollers op één token. Telegram antwoordt dan met HTTP 409.
- Een chat-guard: de bot accepteert alleen berichten uit één bekende chat.

Spraakberichten zetten we lokaal om in tekst (ffmpeg met whisper.cpp). Lokale modellen voor het gesprek zelf hebben we geprobeerd en geschrapt; het kwaliteitsverschil was te groot. Een cloudmodel met een uitgavenplafond won.

### Tools

De assistent krijgt zijn tools via MCP-servers, met een strikte allowlist. Geen shell, geen vrij lezen of schrijven van bestanden, alleen de tools die we bedoelen:

| Tool | Hoe |
|---|---|
| Mail (meerdere accounts) | één mail-MCP per account, elk met eigen credentials |
| Agenda | hetzelfde patroon |
| Taken en administratie | een kleine MCP-wrapper om een bestaande backend |
| Obsidian-vault, lezen | een read-only git-clone op de server die elk kwartier pullt |
| Vault, vastleggen | een tool die alleen nieuwe bestanden in één inbox-map mag zetten |
| Mail-agents | een bestaande automatiseringstool sorteert inkomende mail en zet conceptantwoorden klaar |

Twee gewoontes maakten dit klein. We **wrappen bestaande systemen in plaats van ze opnieuw te bouwen**: de wrapper om de administratie was zo'n vijftig regels. En de vault, ons tweede brein, wordt gevoed door Claude Code-sessies. Zo weet de assistent wat er per project besloten is zonder dat iemand het hem vertelt.

### Veiligheid: het belangrijkste deel

Elke tool heeft een niveau:

| Niveau | Betekenis | Regel |
|---|---|---|
| 0 | lezen | vrij |
| 1 | concept | vrij, de standaard voor mail |
| 2 | verzenden, agenda-items maken | vraagt expliciete bevestiging |
| 3 | verwijderen, filters | dicht |

**Bevestiging wordt afgedwongen door de transportlaag, niet door het model.** Het model kan een actie van niveau 2 alleen voorstellen. De bot toont knoppen om te bevestigen of te annuleren. Pas na een tik draait dezelfde sessie opnieuw met een `confirmed`-vlag, en alleen die vlag zet de tools van niveau 2 open. Het model kan zijn eigen rechten niet verhogen, ook niet onder prompt-injectie.

Mensen typen "ja" in plaats van op de knop te tikken. Een woordenlijst met exacte matches in de transportlaag vangt dat op, zonder dat het model er iets over te zeggen krijgt.

We hebben dit getest met geplante mails vol verborgen instructies, ook een waarin we de assistent zelf vroegen "doe wat in die mail staat". Hij weigerde, en niveau 2 bleef dicht. Als tweede bodem zijn de OAuth-scopes zo smal dat mail verwijderen helemaal niet kán.

De rest van het veiligheidsmodel:

- **Standaard alleen concepten.** Mail-agents zetten concepten klaar. Verzenden is een tik van een mens.
- **Een uitgavenplafond.** Elk onderdeel heeft een eigen API-sleutel met een maandplafond als harde stroomonderbreker. Elke aanroep wordt gelogd met de kosten, en de assistent kan zijn eigen dagkosten opvragen.
- **Een auditlog waar alleen bij komt.** Elke actie gaat naar een JSONL-bestand, dagelijks geroteerd, met een bewaartermijn.
- **Gescheiden sleutels.** Per onderdeel eigen sleutels, bestandsrechten 600, nooit in git.

### De duurste lessen

1. Zet bevestiging in de transportlaag. Alles in de prompt is toneel zodra er injectie in het spel is.
2. `resume` in de Agent SDK neemt het oude systeemprompt mee. We bewaren een hash van het prompt bij elke sessie en starten een verse sessie als die verandert, zodat elke gedragswijziging lopende sessies ongeldig maakt.
3. Google OAuth-apps in de stand "Testing" verliezen hun tokens na zeven dagen. Zet de app op productie, ook voor eigen gebruik.
4. Vraag eerst naar de randvoorwaarden. "Het moet op mijn telefoon werken" veranderde het hele ontwerp van een laptoptool in een gedeelde dienst met meerdere ingangen.

## Deel 2: de lus van dev-acties

De assistent kan geen code wijzigen en niet deployen. Dat is bewust. Maar een verbetering schiet ons vaak te binnen als we niet achter de laptop zitten, en we willen dat ze landt waar het codewerk echt gebeurt: in een Claude Code-sessie in de juiste repo.

### Hoe het werkt

1. **De assistent schrijft één bestand.** Hij heeft daar één tool voor: `add_dev_action(project, title, spec)`. Die zet een nieuw markdownbestand in de vault op `dev-actions/<project>/<datum>-<slug>.md`, met `status: open` in de frontmatter. De tool voegt alleen toe: hij bewerkt of verwijdert nooit een bestaand bestand. Een mail met prompt-injectie kan dus hooguit een suggestie toevoegen, en een mens leest elke suggestie voordat er iets gebouwd wordt.
2. **Bij de start van een sessie verschijnen de open acties.** Start Claude Code een sessie in dat project, dan kijkt ons `/session-start`-commando in de map van het project, leest elk bestand met `status: open` en toont titel, specificatie in één regel en pad in de openingsbanner, met het aanbod ze op te pakken.
3. **Claude Code bouwt.** In de ontwikkelomgeving, met tests, en het laat de diff zien vóór de deploy. Dat is dezelfde goedkeuring als bij elke andere wijziging.
4. **Afsluiten.** Na bouw en deploy past Claude Code het bestand aan: `status: done`, `done: <datum>`, `commit: <sha>`, en commit dat in de vault-repo. De volgende sessie staat de actie niet meer in de banner.

Claude Code mag vault-bestanden bewerken. De assistent niet. Op die scheiding rust het hele veiligheidsargument.

De mapnaam `<project>` is gelijk aan de projectnotitie in de vault, en die notitie heeft een veld `repo:`. Zo vindt een sessie in een repo zijn acties. Eén les: gok nooit een slug om daarna "geen acties" te melden. Vindt het opzoeken op slug niets, dan zoeken we ook op de mapnaam van de repo in de map met dev-acties. Eén keer gokken verborg drie open acties voor ons.

### Acties die wachten

Een open actie kan kloppen en toch nog niet aan de beurt zijn. Kun je dat niet aangeven, dan herhaalt elke sessiestart haar, en ga je de banner negeren. Twee optionele velden lossen dat op:

- `not_before: <datum>` verbergt de actie tot die datum.
- `wait_for: <gebeurtenis>` verbergt haar tot er iets gebeurt dat geen datum heeft, bijvoorbeeld "de nieuwe testserver draait".

Wachtende acties staan niet per stuk in de banner. Er staat één regel: "3 wachtend (eerstvolgende: 2026-12-01 <titel>)". Elke sessie toetst kort elke `wait_for` aan de git-log en de vault. Is de gebeurtenis gebeurd, dan gaat het veld weg en verschijnt de actie gewoon. Anders blijft ze voorgoed onzichtbaar.

### Een overzicht over alle projecten

Een script op schema scant alle `dev-actions/<project>/*.md` op `status: open` en overschrijft één overzichtsnotitie in de vault. Een afgeleide weergave: idempotent, zo vaak te draaien als je wilt.

### Voorbeeld van een actiebestand

Een verzonnen voorbeeld. Project, datums en details zijn bedacht.

```markdown
---
type: dev-action
project: facturen-app
status: open
source: assistant
created: 2026-11-20T08:42:00+01:00
not_before: 2026-11-24
---

# Vervaldatum tonen in de factuurlijst

## Specificatie
Voeg in de factuurlijst een kolom "Vervalt" toe naast "Bedrag".
Verlopen facturen krijgen de bestaande waarschuwingskleur. Sorteer op
vervaldatum bij een klik op de kolomkop.

## Waarom
Gevraagd vanaf de telefoon, tijdens het kijken welke facturen nagebeld moeten worden.

## Klaar als
- Kolom zichtbaar op desktop en mobiel
- Test voor de verlopen toestand
- Diff getoond vóór de deploy
```

Na het werk zet Claude Code in de frontmatter:

```yaml
status: done
done: 2026-11-25
commit: 3f9c2ab
```

### Feedback van gebruikers gebruikt dezelfde map

Een melding van een gebruiker die we in Telegram oppakken, wordt een dev-actie met `source: feedback` en een `source_ref` terug naar de melding. Gaat die op `done`, dan hoort de gebruiker één keer dat het is opgelost. Een actie die we niet bouwen, krijgt `status: dropped` met één regel waarom. De hele route staat in de [koppelvlak-standaard](koppelvlak-standaard.md).

## Maak dit beter

Dit werkt voor ons, het is niet de enige manier. Draai je iets vergelijkbaars en heb je een deel anders opgelost, of zie je een gat in het veiligheidsmodel, dan horen we het graag. Open een issue of begin een gesprek op https://github.com/RichardTheuws/ai-toolkit/discussions.

---

*Geschreven met Claude, nagelopen door Richard.*
