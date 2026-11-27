# Werkafspraken met Claude Code

Dit zijn de werkafspraken die we met Claude Code hebben gemaakt. Geen ervan is slim. De meeste bestaan omdat er iets misging, of steeds weer misging. Per afspraak: de regel, de reden, en hoe we hem afdwingen.

Ze passen bij hoe wij werken: één ontwikkelaar, veel kleine projecten, lange sessies, veel subagents. Bij jou ziet het er anders uit.

## 1. Harde oordelen: PASS, FAIL of KILL

**De regel.** Elk oordeel van de agent landt op PASS, FAIL of KILL. Niet "twijfelgeval", niet "neigt naar FAIL", niet "herzien". Kan hij nog niet beslissen, dan noemt hij de ene meting die het beslist, haalt die op, en geeft dan het oordeel.

**Waarom.** Een zacht oordeel legt de beslissing terug zonder de informatie om hem te nemen. "Marginaal" betekent meestal "ik heb het ding dat ertoe doet niet gemeten". Die meting benoemen maakt van een vaag antwoord een kleine taak. KILL is een echte uitkomst, geen troostprijs.

**Hoe we het afdwingen.** Een korte sectie in de globale `CLAUDE.md`.

## 2. Adviseer, geef geen menu

**De regel.** De agent sluit een blok werk nooit af met "welke kant wil je op?". Hij geeft:

- de aanbeveling;
- waarom déze, onderbouwd met bewijs of het doel;
- waarom niet elk alternatief, één regel per stuk;
- de gevolgen;
- de volgende stap en waaraan we zien dat hij gelukt is;
- "Ik begin hiermee, tenzij je het tegenhoudt."

**Waarom.** Opties zonder voorkeur schuiven het denkwerk terug naar wie de vraag stelde. Juist de afwijzing van elk alternatief in één regel maakt er een advies van, en geen menu met een etiket op één gerecht. "Tenzij je het tegenhoudt" in plaats van een ja/nee-vraag houdt het werk in beweging: we zeggen alleen iets als we het oneens zijn.

**Hoe we het afdwingen.** In `CLAUDE.md`, als deel van een korte sectie over communicatiestijl.

## 3. Feiten zelf, voorkeuren vragen

**De regel.** Is de twijfel feitelijk, dan lost de agent hem zelf op, met code, data, logs of notities. Hij vraagt ons alleen naar echte voorkeuren (risico, scope, beleid, timing) of vóór een onomkeerbare of destructieve stap. Vraagt hij iets, dan alle open vragen tegelijk, in één bericht, als A/B/C-keuze met één keuze gemarkeerd als **(Aanbevolen)** en hooguit twee zinnen per optie.

**Waarom.** Vragen over feiten die de agent zelf kan opzoeken kosten aandacht. Vragen die één voor één binnendruppelen zijn erger. A/B/C met een aanbeveling beantwoord je in tien seconden.

**Hoe we het afdwingen.** In `CLAUDE.md`. Routinestappen waarop het antwoord altijd ja is (deployen na commit en push, opruimen) staan erin als dingen die hij gewoon doet; destructieve stappen (dataverlies, productiemigraties, force push) als dingen waar hij altijd eerst naar vraagt.

## 4. Geen argumenten over hoeveel werk iets is

**De regel.** De agent pleit nooit voor of tegen een optie op basis van hoeveel werk het is. Geen "dat is veel werk", geen "ongeveer tien uur", geen "te zwaar". Hij redeneert terug vanuit het doel. Werk schat hij alleen in als we erom vragen, of als het nodig is voor de volgorde.

**Waarom.** Voor een agent is bouwen niet meer de beperking die het was. "Dat is een flinke klus" trekt keuzes naar de kleinere optie, ook als de grotere de juiste is voor het project. Moeite is een planningsvraag, geen argument.

**Hoe we het afdwingen.** Eén alinea in `CLAUDE.md`.

## 5. Subagents leveren beslissingen, geen vragen

**De regel.** Een subagent eindigt nooit met "open vragen voor de gebruiker". Keuzemomenten komen terug als beslissingen met een aanbeveling per punt. De hoofdsessie zet wat echt een mens nodig heeft om in één A/B/C-bericht in de chat. Elke subagent laat ook een korte, gedateerde "yield"-notitie achter: wat hij vond, wat hij aanbeveelt, welke bestanden hij raakte, hoe zeker hij is. Een mens beslist wat daarvan, als er al iets is, bewaard blijft.

**Waarom.** Bij een run van vier subagents naast elkaar leverde er één een document op dat eindigde met vijf open vragen. Een subagent heeft geen kanaal terug naar de gebruiker, maar dat is geen reden om vragen in een document te parkeren: een document dat eindigt met "wat wil je?" moet je met de hand uitpluizen. De yield-notities dienen als spoor van wat agents deden, en als invoer voor de review aan het eind van de sessie. We kozen bewust voor geen automatische promotie: yields zijn ruw materiaal, en een mens filtert.

**Hoe we het afdwingen.** Een vaste regel in elke subagent-prompt: lever keuzemomenten als beslissingen met een aanbeveling, nooit als open vragen voor de eindgebruiker. Een kort contract legt het yield-formaat vast (een paar verplichte frontmatter-velden, vijf tot tien regels tekst, een bestandsnaam met datum per agent). Het commando aan het eind van de sessie bekijkt de verse yields en stelt hooguit twee dingen voor om vast te leggen.

## 6. Een les die terugkomt, wordt een hook

**De regel.** Komt dezelfde fout een tweede keer terug terwijl er al een geschreven les over bestaat, dan breiden we de les niet verder uit. We bouwen een controle die draait op het moment van de fout: een `PreToolUse`-hook, of een vast script waar het recept in zit.

**Waarom.** Eén deployfout met `rsync --delete` stond in een paar maanden zes keer als les opgeschreven. Een zsh-valkuil (`$var:latest`, waarbij zsh `:l` als modifier leest) stond vijf keer in een deploydocument. Toch gingen ze allebei opnieuw mis: een productie-`.env` werd gewist en een rollbacktag mislukte. Een les wordt gelezen als hij relevant lijkt, maar na een contextsamenvatting bouwt de agent een commando na uit het geheugen, en dan is de les niet in beeld. Tekst is advies, een hook is een poort.

**Hoe we het afdwingen.** De shell-bewaker in [`hooks/bash-guard/`](../../hooks/bash-guard/) blokkeert precies de drie fouten die terugkwamen: `rsync --delete` zonder bescherming van `.env` of met opties in een stringvariabele, modifiers in de stijl van `$var:latest`, en "testen, dan committen" aan elkaar geregen met `;` (dan gaat de commit ook door als de tests falen). Voor we een regel toevoegen, spelen we hem af tegen de Bash-historie in oude sessietranscripten, om te zien hoeveel vals alarm hij zou geven.

**De tegenles: een poort kan doorschieten.** We bouwden ook een review-poort: een `Stop`-hook die het einde van een beurt blokkeerde tot risicovolle wijzigingen (migraties, auth, betalingen, deployscripts, grote diffs) een code-review hadden gehad. De aanleiding was echt: een set verhuisscripts voor servers had twee dagen zonder review gedraaid, en de eerste review vond tien fouten. Maar de poort sloeg veel te vaak aan: 147 reviews in zes dagen, tegen 8 in de week ervoor. En een `Stop`-hook in combinatie met een review-skill die op de achtergrond draait gaf een lus: de beurt eindigde terwijl de review nog liep, de hook zag "geen review" en blokkeerde opnieuw, en soms startte het model een tweede. We zetten hem uit en gingen naar één review per sessie. Een latere telling liet nog steeds 91 reviews in drieënhalve dag zien, en de opvolging kostte anderhalf keer de review zelf, omdat de hele lijst zonder weging werd gefixt en daarna opnieuw gereviewd.

Dus start de agent nu nooit zelf een review. Het commando aan het eind van de sessie geeft alleen een advies, en we starten de review zelf, met een vast recept: één repo, alleen afgerond werk, een niveau gekozen op omvang en gevoeligheid van de diff, eerst elke bevinding wegen (nu / backlog / vervalt), een falende test vóór elke fix, de backlogpunten samen in één vervolgnotitie, en geen tweede review van de fixes. De tests zijn de controle.

Wat we uit allebei haalden: een hook past bij een fout die goedkoop te herkennen en duur om te maken is, niet bij een afweging die alleen soms moet gebeuren. En een `Stop`-hook die zelf achtergrondwerk uitlokt, moet weten dat dat werk nog loopt.

## 7. Ruim CLAUDE.md af en toe op

**De regel.** Haal periodiek instructies weg die zwaktes van oudere modellen opvingen. Houd de kernregels, die het doel en de grenzen beschrijven, ongewijzigd. Archiveer skills en commando's die niemand gebruikt, op basis van echt gebruik, niet op gevoel. Houd `CLAUDE.md` onder versiebeheer.

**Waarom.** Onze globale `CLAUDE.md` was gegroeid tot 369 regels: regels over toolgebruik, zoekprotocollen, verouderde statusnotities, en autonomieregels die elkaar tegenspraken en het gedrag al stuurden. "Alles weg en kijken wat breekt" vonden we geen goed idee: de kernregels verdwijnen dan, en de schade zie je pas later. Na het opruimen: 214 regels. Vijftien commando's en dertien skills gingen naar het archief (omkeerbaar), gekozen op basis van elf maanden commandogeschiedenis.

**Hoe we het afdwingen.** Het bestand staat in een git-repo, met een symlink vanuit `~/.claude/` en een eigen changelog. Transcripten bewaren we lang genoeg om de volgende keer het gebruik te meten.

## 8. Wees open over AI

**De regel.** We verhullen nooit dat we AI gebruiken. Geen tooling, prompts of teksten die bedoeld zijn om "minder als AI te klinken", "ondetecteerbaar" te zijn of detectors te omzeilen. Tekst opschonen mag, als het om schrijfkwaliteit gaat: helderder, specifieker, in onze eigen stem. "Is dit met AI gemaakt?" krijgt altijd een eerlijk antwoord. In berichten aan anderen gebruiken we alleen wat iemand zelf publiek deelde of ons rechtstreeks vertelde; nooit verzonnen vertrouwdheid, cijfers of resultaten.

**Waarom.** Het is een ethische grens, geen stijlkeuze. Schrijfhulp die bestaat om de lezer te misleiden, bouwen en gebruiken we niet.

**Hoe we het afdwingen.** Een korte sectie in `CLAUDE.md`, en een transparantiepoort in [`skills/li-check/`](../../skills/li-check/): elk concept voor buitenstaanders gaat erdoor, en hij faalt op alles wat AI-gebruik ontkent, open placeholders, of interne notities die in publieke tekst lekken. De notitie onderaan deze playbook volgt dezelfde regel.

## 9. Test voor je zegt dat het werkt; klaar is geverifieerd in productie

**De regel.** De agent draait linters, typechecks, de bestaande tests en de randgevallen voor hij zegt dat iets werkt. Nieuwe features krijgen tests in dezelfde sessie, zonder dat we erom vragen. Test ook tegen productiegrenzen (URL-lengte, batchgroottes, echte datavolumes), niet alleen tegen fixtures. Een taak is klaar als hij gedeployd is en de live versie (health-endpoint of `VERSION`) de nieuwe laat zien. Falen de tests na een deploy, dan fixen en opnieuw deployen.

**Waarom.** "Code af" en "werkt voor de gebruiker" zijn twee verschillende toestanden. Caches, een deploy die niet aankwam, en fixtures die veel kleiner zijn dan echte data zitten er allemaal tussen.

**Hoe we het afdwingen.** In `CLAUDE.md`, plus deploycommando's die we letterlijk uit een deployscript of `DEPLOY.md` nemen, nooit uit het geheugen, en de shell-bewaker uit afspraak 6.

## Kopieer dit naar je eigen CLAUDE.md

```markdown
## Werkafspraken
- Oordelen: elk oordeel eindigt op PASS / FAIL / KILL. Nooit "twijfelgeval". Kun je niet
  beslissen, noem dan de ene meting die het beslist, haal die op, en beslis.
- Adviseer, geef geen menu: aanbeveling, waarom deze, waarom niet elk alternatief (één regel
  per stuk), gevolgen, volgende stap + succescriterium, "Ik begin hiermee, tenzij je het tegenhoudt".
- Los feitelijke twijfel zelf op (code, data, logs). Vraag alleen naar echte voorkeuren of
  vóór onomkeerbare stappen; stel alle vragen tegelijk, als A/B/C met één (Aanbevolen).
- Pleit nooit voor of tegen een optie op basis van hoeveel werk het is. Redeneer vanuit het doel.
- Subagents: lever keuzemomenten als beslissingen met een aanbeveling, nooit als open vragen
  voor de gebruiker. Laat een korte gedateerde notitie achter: bevindingen, aanbeveling,
  bestanden, zekerheid.
- Een fout die terugkomt ondanks een geschreven les krijgt een hook of een script, geen langere les.
- Verhul nooit AI-gebruik. Geen "ondetecteerbare" of detector-omzeilende tekst. "Is dit met AI
  gemaakt?" krijgt altijd een eerlijk antwoord.
- Test voor je zegt dat het werkt. Klaar = gedeployd en de live versie gecontroleerd, niet "code af".
```

## Maak dit beter

Dit zijn de onze, en ze blijven veranderen. Heb je werkafspraken met je coding-agent die standhielden, of werkte een van de onze bij jou niet? Dat horen we graag: [github.com/RichardTheuws/ai-toolkit/discussions](https://github.com/RichardTheuws/ai-toolkit/discussions).

---

*Geschreven met Claude, nagelopen door Richard.*
