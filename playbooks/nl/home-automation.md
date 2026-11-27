# Eén app voor het hele huis

We hadden vijf apps van fabrikanten voor één huis. Sommige werkten slecht, niet iedereen in het gezin had toegang, en geen ervan kon iemand toegang geven voor een bepaalde periode. Dus bouwden we met Claude Code één privé-webapp die alles bedient.

De code zelf publiceren we niet. Die hoort bij één huis: de ruimtes, de apparaten, de mensen. Hieronder staat het patroon, en wat ons onderweg beet.

## De opbouw

- **Eén thuisserver.** Een Mac mini M4 draait de app als container, achter dezelfde Caddy en Cloudflare-tunnel als onze andere apps (zie [draaien-op-een-mac-mini.md](draaien-op-een-mac-mini.md)). Python, SQLite en gewoon JavaScript, geen framework.
- **Inloggen met passkeys.** Geen wachtwoorden om te delen of te resetten. Toegang stel je in per persoon, per plek, per ruimte en per periode, zodat een gast voor een beperkte tijd bij één ruimte kan.
- **Eén koppeling per systeem.** Homebridge (op een Raspberry Pi in huis), Eufy voor camera's en deurbel (via de Homebridge-plugin), tado voor de verwarming (cloud), Tuya voor stekkers en lampen (cloud), en nog een paar. Elke koppeling is een kleine module met eigen tests tegen een nepversie van dat systeem.
- **Eén app in plaats van vijf.** Een plattegrond waarop elke ruimte gloeit in de kleur van zijn echte lampen. Tik op een ruimte en de standen komen tevoorschijn: Vol, Zacht, Gedempt, Uit, plus een paar extra's. Een stand afstellen doe je door de lampen met de hand goed te zetten en op "Bewaar huidig licht" te drukken.

**Waarom geen Home Assistant?** We hebben overwogen Home Assistant eronder te zetten met een eigen voorkant erbovenop, en kozen ervoor de koppelingen zelf te bouwen. Dat kost iets: verandert een fabrikant zijn API, dan is de reparatie aan ons. Daar staat tegenover dat we de schermen, de toegangsregels en de vormgeving zelf in de hand hebben.

## Wat ons beet

**Docker op macOS bereikt geen broadcast of multicast op het thuisnetwerk.** Een tv wekken met Wake-on-LAN en apparaten zoeken via mDNS of SSDP lukt niet vanuit een container. Nu wekt de app apparaten via Homebridge op de Pi, die zelf op het netwerk zit, en vindt hij apparaten via vaste startadressen plus de eigen topologie van het systeem.

**De cloud-API zegt "gelukt" terwijl het apparaat het commando negeerde.** Een Tuya-lamp neemt hooguit acht stappen in een scène. Met twaalf gaf de API `success: true` en hield de lamp zijn oude scène. Nu lezen we na elk scènecommando de status terug en vergelijken we.

**Een plugin-update vroeg om een andere Pi.** De Eufy-plugin V5 wil Node 24, en dat bestaat niet voor 32-bit ARM, dus de Pi moest naar een 64-bit systeem. De plugin moet ook inloggen met het land van het hoofdaccount, en de config heeft het nieuwe platformblok nodig.

**Telefoons hielden het oude JavaScript vast.** Cloudflare cachet `.js` en `.css` urenlang. Nu dragen scripts en stijlen het versienummer in hun adres.

**Camerabeelden kwamen laat binnen.** Een RTSP-stroom via ffmpeg gaf het eerste beeld na 16 tot 19 seconden. Het `fps`-filter en de standaardbuffers hielden beelden vast. Nu: geen filter, `-fps_mode passthrough` en invoeropties voor lage vertraging (`-fflags nobuffer -flags low_delay`). Eerste beeld in zo'n 2 seconden.

**Het scherm vocht met de gebruiker.** Verversen op de achtergrond kon een knop vlak na een tik terugzetten. Nu wordt een antwoord dat ouder is dan je laatste tik genegeerd, en wacht verversen zolang je een schuif vasthoudt. Alle systemen worden tegelijk gelezen, zodat één trage cloud de rest niet meer ophoudt.

## Projectieshows op een goedkope beamer

We maakten van een goedkope Android 14-beamer (1 GB RAM, 1280×720) een vaste showmachine: projection mapping met Halloween en een show op een plafond met Kerst.

- **De show draait op de beamer zelf,** als eigen app, niet via HDMI vanaf een laptop. De app heeft een kleine lokale webserver aan boord, omdat `fetch()` geen `file://` accepteert. Valt de wifi weg, dan draait de show door.
- **Een WebGL-engine met een masker per vlak.** In een mapping-editor tekenen we elk onderdeel van het gebouw op de live projectie: handgrepen, punten, ongedaan maken, exporteren naar JSON. Zachte maskers laten licht zonder naad over meerdere vlakken lopen.
- **Een kalibratietool.** De beamer toont Gray-code-patronen, een webcam neemt ze op, en elk camerapixel krijgt zijn beamerpixel. Vlakken die in het camerabeeld zijn aangewezen, worden omgerekend naar de mapping. Is de beamer verschoven: scan, map, check.
- **Geheugen is de grens, niet de GPU.** Alle geluiden tegelijk decoderen kostte zo'n 300 MB. Nu laadt het geluid per film, in mono, en rendert het canvas op twee derde van de resolutie.

Twee lessen kostten ons de meeste tijd:

**Automatisch starten lukt alleen als de app eigenaar van het apparaat is.** Op Android 14 draaide onze boot-receiver wel, maar de activity kwam nooit in beeld (`BAL_BLOCK` in logcat). Een root-proces van de fabrikant zette bij elke start zijn eigen launcher weer aan. Wat werkte: onze app device owner maken (`dpm set-device-owner <pkg>/.AdminReceiver`, alleen mogelijk zolang er geen accounts op het apparaat staan). Een device owner mag vanuit de achtergrond starten, zet zichzelf als HOME en pint zichzelf met lock task. Wil je later tussen launchers wisselen, verberg dan de andere launcher via de device owner in plaats van voorkeuren op te stapelen. Test beide richtingen, en een herstart.

**Wacht na het opstarten zo'n twee minuten met ADB.** ADB nam de verbinding aan maar beantwoordde de handdruk niet. Het leek op een ingetrokken sleutel; het was timing. Nu wachten scripts tot de poort open is en dan nog twee minuten. We zetten ook `settings put global adb_allowed_connection_time 0`, zodat de sleutel niet na zeven dagen vervalt.

## Android-tv's opschonen

Voor de tv's gebruikten we [tv-home](https://github.com/mihirgupta0900/tv-home) van mihirgupta0900, een open-sourceproject onder de MIT-licentie. Je geeft Claude Code één prompt en die schoont een Android TV of Google TV op via ADB (uitschakelen, nooit verwijderen), zet er een minimaal startscherm op en schrijft een herstelscript. De eer voor de aanpak is aan hen.

Eén ding voegden we toe: het venster van de launcher moet expliciet ondoorzichtig zijn (`windowIsTranslucent`, `windowIsFloating` en `windowShowWallpaper` op false). Het firmwarethema markeerde het als doorzichtig, waardoor de app eronder na een druk op Home bleef draaien en in beeld bleef. Controleer met `dumpsys activity activities`: de home-taak hoort `translucent=false` te zijn, de app eronder `STOPPED`.

## Maak dit beter

Heb je iets vergelijkbaars gebouwd? We horen graag wat jou beet en wat je anders doet. Open een issue of een draad op https://github.com/RichardTheuws/ai-toolkit/discussions.

---

Geschreven met Claude, nagelopen door Richard.
