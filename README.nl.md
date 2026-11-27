# ai-toolkit

[English](README.md) · **Nederlands**

Gereedschap en aantekeningen uit ons dagelijks werk met Claude Code: hooks,
commands, skills, templates en playbooks. Alles begon als oplossing voor iets dat
in ons eigen werk misging. We hebben het opgeschoond zodat jij het kunt gebruiken,
en we horen graag wat jij anders zou doen. Daarvoor publiceren we het: samen
worden we hier beter in.

Van Richard Theuws ([theuws.com](https://theuws.com)), gebouwd samen met Claude.
**De gids**: [tools.theuws.com/nl/](https://tools.theuws.com/nl/) legt per hoofdstuk uit hoe deze tools samenwerken, met schermafbeeldingen.

De code en de README's per tool zijn in het Engels. De playbooks staan in beide
talen.

## Wat erin zit

### Hooks: regels die Claude Code afdwingt, niet alleen leest

| Tool | Wat het doet |
|---|---|
| [bash-guard](hooks/bash-guard/) | Houdt drie shell-fouten tegen die steeds terugkwamen: `rsync --delete` die een `.env` kan wissen, zsh-valkuilen als `$var:x`, en tests die met `;` aan een push vastzitten |
| [session-tracker](hooks/session-tracker/) | Eén logregel per sessie (project, begin, eind, duur), zodat een nieuwe sessie weet waar de vorige ophield |
| [vault-context](hooks/vault-context/) | Geeft Claude bij de start de vault-notitie van het project waarin je zit |
| [compact-recovery](hooks/compact-recovery/) | Vertelt Claude na het samenvatten van het gesprek de branch, de openstaande wijzigingen en de laatste commits |
| [sound-cues](hooks/sound-cues/) | Een geluid als Claude klaarstaat, bezig is, vastloopt of klaar is, zodat je niet naar de terminal hoeft te kijken |

### Commands

| Command | Wat het doet |
|---|---|
| [/session-start](commands/session-start.md) | Begint elke sessie hetzelfde: git, vorige sessie, geheugencheck, vault-notitie, open acties |
| [/decision](commands/decision.md) | Legt een architectuurbeslissing vast als gedateerd markdownbestand |
| [/learning](commands/learning.md) | Legt een les vast, en waarschuwt als dezelfde les steeds terugkomt |

### Scripts

| Script | Wat het doet |
|---|---|
| [memory-audit](scripts/memory-audit/) | Geeft het auto-geheugen van een project groen, oranje of rood, en zegt wat er beter moet |
| [leak-gate](scripts/leak-gate/) | Weigert een map te publiceren met geheimen, thuismappen, interne IP's of namen van je eigen denylist |

### Skills

| Skill | Wat het doet |
|---|---|
| [li-check](skills/li-check/) | Kwaliteitscheck voor LinkedIn-concepten, met een harde transparantiepoort: helpt nooit AI-gebruik te verbergen |

### Templates

| Template | Wat het is |
|---|---|
| [mcp-backend-wrapper](templates/mcp-backend-wrapper/) | De API van je eigen app achter MCP zetten, als tools voor Claude Code |

### Playbooks: hoe we werken, en waar we ons aan brandden

| Nederlands | English |
|---|---|
| [Werkafspraken met Claude Code](playbooks/nl/werkafspraken.md) | [Working agreements](playbooks/working-agreements.md) |
| [Geheugenhygiëne](playbooks/nl/geheugenhygiene.md) | [Memory hygiene](playbooks/memory-hygiene.md) |
| [Obsidian als gedeeld geheugen](playbooks/nl/obsidian-als-gedeeld-geheugen.md) | [Obsidian as shared memory](playbooks/obsidian-as-shared-memory.md) |
| [Een persoonlijke assistent die werk doorgeeft aan een coding agent](playbooks/nl/persoonlijke-assistent.md) | [Personal assistant](playbooks/personal-assistant.md) |
| [Een koppelvlak-standaard voor je eigen systemen](playbooks/nl/koppelvlak-standaard.md) | [Integration standard](playbooks/integration-standard.md) |
| [Apps van Claude draaien op een Mac mini](playbooks/nl/draaien-op-een-mac-mini.md) | [Running on a Mac mini](playbooks/running-on-a-mac-mini.md) |
| [Eén app voor het hele huis](playbooks/nl/home-automation.md) | [One app for the whole house](playbooks/home-automation.md) |

### In een eigen repository

| Project | Wat het doet |
|---|---|
| [video-studio](https://github.com/RichardTheuws/video-studio) | Een Claude Code-skill die vanuit de chat een af filmpje maakt: monteren of genereren, met een akkoordstap vóór betaalde renders |
| [VOX](https://github.com/RichardTheuws/VOX-app) | Menubalk-app voor macOS die AI-antwoorden uit terminal en editors voorleest, op het apparaat zelf |
| [FalconDebugger](https://github.com/RichardTheuws/FalconDebugger) | Plugin om WordPress te debuggen |

## Proberen met een demovault

`examples/demo-vault` is een kleine verzonnen vault (één project, twee beslissingen, een les, twee dev-acties). Zet `VAULT_DIR` erop om de hooks en commands te proberen voordat je je eigen notities gebruikt.

## Gebruiken

Je hoeft niets in z'n geheel te installeren. Elke map heeft een eigen README met
een installatie om te kopiëren, en bijna alles draait op wat macOS al heeft
(bash, Python 3, Node). Werkt iets alleen op macOS, of is er een betaalde API voor
nodig, dan staat dat in de README.

## Wat we weglieten, en waarom

Een deel van ons gereedschap hoort bij één leven, één huis of één klant: onze
persoonlijke assistent, de app voor thuis, klantwerk, onze betaalde producten. Dat
blijft privé. Waar het *patroon* nuttig is, staat het in een playbook.

Alles hier is naar een nieuwe repository gekopieerd, nooit vanuit een privé-repo
geforkt, en elke push gaat door [leak-gate](scripts/leak-gate/).

## Maak dit beter

- **Iets kapot of onduidelijk?** [Open een issue](https://github.com/RichardTheuws/ai-toolkit/issues/new/choose).
- **Jij doet het anders, of beter?** Begin een [discussie](https://github.com/RichardTheuws/ai-toolkit/discussions). Nederlands mag.
- **Een fix, of een nieuwe regel met een test?** Pull requests zijn welkom; zie [CONTRIBUTING.md](CONTRIBUTING.md).

## Licentie

MIT, zie [LICENSE](LICENSE). `skills/li-check` is afgeleid van Jake Schincariols
[linkedin-agent-skill](https://github.com/Jakeschincariol/linkedin-agent-skill)
(MIT) en houdt diens vermelding.
