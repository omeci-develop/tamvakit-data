#!/usr/bin/env python3
"""Wache auf die **ausgelieferten** Gebetszeiten-Buendel.

Warum es diese Wache gibt
-------------------------
Am 2026-09-14 verloren **alle 1.200 deutschen Orte** ihre amtlichen
Gebetszeiten. `all-DE.json` war seit dem 25.08. eingefroren — der
Veroeffentlichungs-Lauf im App-Repo startete wegen der Abrechnung nicht mehr —
und deckte nur 2026-08-25 bis 2026-09-13 ab. Aufgefallen ist es durch eine
Nutzermeldung, drei Wochen spaeter.

Es *gab* eine Alarmierung: Der Lauf legt bei einem **roten** Durchgang ein
Issue an. Er ist aber nie gelaufen — und **Stille ist kein Fehlschlag**. Fuer
„seit N Tagen nicht gelaufen" hatte niemand etwas.

Diese Wache prueft deshalb nicht den Job, sondern **sein Ergebnis**: das, was
unter data.tamvakit.app tatsaechlich ausgeliefert wird. Damit faengt sie jede
Ursache ab, egal ob der Lauf ausblieb, rot war, oder der Pages-Build haengt —
und auch ein abgelaufenes Zugriffs-Token, das sonst wieder ein stiller Ausfall
waere.

Warum ueber HTTP und nicht gegen die Dateien im Repo
----------------------------------------------------
Weil die Zusage an den Nutzer das **Ausgelieferte** ist, nicht der Stand im
Repo. Dieselbe Begruendung wie bei `live_legal_site_test.dart` im App-Repo, das
bewusst die echte Website prueft. Ein haengender Pages-Build faellt nur so auf.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone

BASIS = os.environ.get("DATEN_BASIS", "https://data.tamvakit.app").rstrip("/")

# Muss zu `kMinCoverageDays` in der App passen
# (lib/features/prayer_times/data/diyanet/diyanet_cached_times.dart).
# Faellt der Vorrat darunter, laedt die App nach — kann sie das nicht, rechnet
# sie offline weiter und der Nutzer verliert die amtlichen Zeiten.
MIN_TAGE = 14

# Der Veroeffentlichungs-Lauf geht woechentlich (montags). Zehn Tage lassen
# einen ausgefallenen Lauf durchgehen, zwei hintereinander nicht.
MAX_ALTER_TAGE = 10

ZEITLIMIT = 60


def hole(pfad: str) -> object:
    with urllib.request.urlopen(f"{BASIS}/{pfad}", timeout=ZEITLIMIT) as res:
        if res.status != 200:
            raise RuntimeError(f"HTTP {res.status}")
        return json.loads(res.read().decode("utf-8"))


def schluessel(tag: date) -> str:
    return tag.isoformat()


def pruefe_land(land: str, heute: date) -> list[str]:
    """Klagen ueber ein Laender-Buendel — leere Liste heisst: in Ordnung."""
    try:
        daten = hole(f"all-{land}.json")
    except (urllib.error.URLError, OSError, ValueError, RuntimeError) as fehler:
        return [f"{land}: all-{land}.json nicht abrufbar ({fehler})"]

    if not isinstance(daten, dict) or "cities" not in daten:
        return [f"{land}: unerwartetes Format (kein Umschlag mit `cities`)"]

    klagen: list[str] = []

    roh = daten.get("updated")
    if isinstance(roh, str):
        try:
            erzeugt = datetime.fromisoformat(roh.replace("Z", "+00:00"))
            alter = (datetime.now(timezone.utc) - erzeugt).days
            if alter > MAX_ALTER_TAGE:
                klagen.append(
                    f"{land}: seit {alter} Tagen nicht neu erzeugt "
                    f"(updated {roh[:10]}, erlaubt {MAX_ALTER_TAGE})"
                )
        except ValueError:
            klagen.append(f"{land}: `updated` unlesbar ({roh!r})")

    orte = daten["cities"]
    if not isinstance(orte, dict) or not orte:
        return klagen + [f"{land}: Buendel ohne Orte"]

    ohne_heute = 0
    ohne_vorrat = 0
    letzter: str | None = None
    for eintrag in orte.values():
        tage = eintrag.get("days") if isinstance(eintrag, dict) else None
        if not isinstance(tage, dict) or not tage:
            ohne_heute += 1
            continue
        if letzter is None:
            letzter = max(tage)
        if schluessel(heute) not in tage:
            ohne_heute += 1
        if schluessel(heute + timedelta(days=MIN_TAGE - 1)) not in tage:
            ohne_vorrat += 1

    if ohne_heute:
        klagen.append(
            f"{land}: {ohne_heute} von {len(orte)} Orten haben HEUTE keine "
            f"Zeiten (letzter Tag im Buendel: {letzter})"
        )
    elif ohne_vorrat:
        klagen.append(
            f"{land}: {ohne_vorrat} von {len(orte)} Orten reichen keine "
            f"{MIN_TAGE} Tage mehr (letzter Tag: {letzter})"
        )
    return klagen


def main() -> int:
    heute = datetime.now(timezone.utc).date()
    print(f"Wache laeuft gegen {BASIS}, Stichtag {heute}\n")

    try:
        index = hole("index.json")
    except (urllib.error.URLError, OSError, ValueError, RuntimeError) as fehler:
        print(f"✗ index.json nicht abrufbar ({fehler}) — ohne ihn sagt kein "
              f"Befund unten etwas.")
        return 1

    # Kontrollwert: Ein leerer Index beantwortete jede Pruefung unten mit
    # „nichts zu tun" — und genau das waere der Schaden, nicht das Ergebnis.
    orte = index.get("cities") if isinstance(index, dict) else index
    if not isinstance(orte, list) or len(orte) < 2000:
        anzahl = len(orte) if isinstance(orte, list) else "?"
        print(f"✗ Index traegt nur {anzahl} Orte (erwartet >= 2000). "
              f"Das ist ein Datenverlust, keine Abdeckungsfrage.")
        return 1

    laender = sorted({o["country"] for o in orte if isinstance(o, dict) and o.get("country")})
    print(f"Index: {len(orte)} Orte, {len(laender)} Laender ({', '.join(laender)})\n")

    klagen: list[str] = []
    for land in laender:
        befund = pruefe_land(land, heute)
        print(f"  {'✗' if befund else '✓'} {land}" + (f" — {befund[0]}" if befund else ""))
        for weiterer in befund[1:]:
            print(f"      {weiterer}")
        klagen += befund

    if not klagen:
        print(f"\n✓ Alle {len(laender)} Buendel tragen heute und die naechsten "
              f"{MIN_TAGE} Tage.")
        return 0

    print("\n".join(["", "✗ Buendel ohne ausreichende Abdeckung:", *klagen]))
    print(
        "\nDas ist fast nie ein Fehler der App, sondern ein stehengebliebener "
        "Veroeffentlichungs-Lauf: Er erzeugt die Buendel neu, und laeuft er "
        "nicht, schmilzt jedes rollierende Fenster taeglich ab. Die "
        "Einzelort-Dateien (city/<id>.json, ein volles Jahr) sind davon nicht "
        "betroffen — die App faellt auf sie zurueck, zahlt dafuer aber mit "
        "Datenvolumen und gibt die Stadt preis (Datenschutz-Stufe 3)."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
