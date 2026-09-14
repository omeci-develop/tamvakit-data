# Tam Vakit — veröffentlichte Gebetszeiten

Statische Gebetszeiten-Daten für die App **Tam Vakit** (Omeci Labs).

## Quelle und Danksagung

Alle Gebetszeiten stammen von der **Diyanet İşleri Başkanlığı** (Präsidium für
Religionsangelegenheiten der Türkei), bezogen über deren offizielle
[Awqat Salah API](https://awqatsalah.diyanet.gov.tr). Die Zeiten werden
**unverändert** übernommen — es findet keine eigene Neuberechnung statt.

*Namaz vakitleri Diyanet İşleri Başkanlığı'nın resmî Awqat Salah API'sinden
alınmaktadır ve değiştirilmeden yayımlanmaktadır.*

## Warum dieses Repo existiert

Die API ist eng rate-limitiert (nach der Einführungsphase ~5 Anfragen pro Tag und
Endpoint **pro Konto**). Würde jedes Endgerät selbst abfragen, wäre die Quote nach
wenigen Nutzern erschöpft. Stattdessen holt ein zentraler Job die Daten **einmal**
und legt sie hier ab — die Last auf Diyanets Servern bleibt dadurch **konstant,
unabhängig von der Nutzerzahl**, und in der App müssen keine Zugangsdaten stecken.

## Aufbau

| Datei | Inhalt |
| --- | --- |
| `index.json` | Alle Orte mit Koordinaten, für die Zeiten vorliegen |
| `city/<id>.json` | Rollierender 32-Tage-Block für einen Ort |

`index.json` — ein Eintrag je Ort:

```json
{ "id": 11019, "name": "KOLN", "country": "DE",
  "region": "NORDRHEIN-WESTFALEN", "lat": 50.938361, "lng": 6.959974,
  "fetched": "2026-08-09T20:25:18Z", "priority": 0 }
```

`city/<id>.json` — Tage unter `days`, Schlüssel `yyyy-MM-dd` (Ortsdatum), Zeiten
als `HH:mm` **in Ortszeit** mit `greenwichMeanTimeZone` als UTC-Versatz:

```json
{ "city": { ... }, "fetched": "...",
  "days": { "2026-08-08": { "fajr": "04:08", "sunrise": "06:01",
    "dhuhr": "13:43", "asr": "17:47", "maghrib": "21:15", "isha": "22:56",
    "gregorianDateShort": "08.08.2026", "greenwichMeanTimeZone": 2 } } }
```

## Aktualisierung

Ein wöchentlicher GitHub-Actions-Job im (privaten) App-Repo erneuert die
ältesten Orte im Rahmen des Kontingents. Ein Block deckt 32 Tage ab und wird
nach ~3 Wochen erneuert; die Zahl gleichzeitig versorgbarer Orte ist dadurch
begrenzt.

**Diese Dateien werden maschinell geschrieben — bitte nicht von Hand ändern.**

## Wache

[`scripts/daten_wache.py`](scripts/daten_wache.py) prüft täglich
([`.github/workflows/daten-wache.yml`](.github/workflows/daten-wache.yml)), ob
das **Ausgelieferte** noch trägt: Ist jedes Länder-Bündel jung genug, deckt es
heute plus die nächsten 14 Tage ab, und steht jeder Ort aus dem Index
überhaupt noch darin? Reißt eine dieser Zusagen, entsteht ein Issue in diesem
Repo.

**Warum es sie gibt.** Am 2026-09-14 verloren alle 1.200 deutschen Orte ihre
amtlichen Zeiten: `all-DE.json` war seit dem 25.08. eingefroren. Es *gab* eine
Alarmierung — aber nur für **rote** Läufe, und der Veröffentlichungs-Lauf war
nie rot: Erst startete er sechs Tage lang gar nicht (Abrechnung), dann brach er
fünf Tage an einem Zwischenschritt ab, und danach lief er **grün und untätig**,
weil seine Vorprüfung das Alter des Abrufs maß statt der Reichweite der Daten.
Stille ist kein Fehlschlag — und ein grüner Lauf ist kein Ergebnis. Deshalb
prüft die Wache nicht den Job, sondern sein Ergebnis über HTTP, so wie eine
ausgelieferte App es sieht.

Von Hand: `python3 scripts/daten_wache.py` (oder gegen eine andere Quelle mit
`DATEN_BASIS=…`). Ihre Regeln selbst prüft `scripts/daten_wache_test.py`
(ohne Netz, läuft im Workflow vorweg).
