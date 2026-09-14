#!/usr/bin/env python3
"""Prueft die Regeln in `daten_wache.py` — ohne Netz.

Warum es diesen Test gibt: Die Wache ist die letzte Instanz zwischen einem
stillen Datenausfall und den Nutzern. Eine Wache, deren Regel niemand geprueft
hat, ist eine Vermutung. Jeder Fall unten setzt genau eine Sache aus.

    python3 scripts/daten_wache_test.py
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta, timezone

import daten_wache as wache

HEUTE = date(2026, 9, 14)
JETZT = datetime(2026, 9, 14, 6, 12, tzinfo=timezone.utc)


def buendel(orte: dict[str, int], *, alter_tage: int = 0) -> dict:
    """Ein Buendel: {Ort-Kennung: wie viele Tage es ab heute traegt}."""
    return {
        "schema": 1,
        "updated": (JETZT - timedelta(days=alter_tage)).isoformat(),
        "cities": {
            kennung: {
                "days": {
                    (HEUTE + timedelta(days=i)).isoformat(): {"fajr": "04:20"}
                    for i in range(tage + 1)
                }
            }
            for kennung, tage in orte.items()
        },
    }


def lauf(daten: dict, erwartet: list[dict] | None = None) -> list[str]:
    wache.hole = lambda pfad: daten  # noqa: ARG005 — Netz ersetzt
    return wache.pruefe_land("TR", HEUTE, erwartet)


GEZAEHLT = {"faelle": 0, "fehler": 0}


def pruefe(was: str, klagen: list[str], *, erwartet_klage: bool) -> None:
    ok = bool(klagen) == erwartet_klage
    GEZAEHLT["faelle"] += 1
    GEZAEHLT["fehler"] += 0 if ok else 1
    print(
        f"  {'✓' if ok else '✗'} {was}"
        + (f" — {klagen[0]}" if klagen else "")
        + ("" if ok else f"  [erwartet {'eine Klage' if erwartet_klage else 'keine Klage'}]")
    )


print("daten_wache:")

# Kontrollwert: Ein gesundes Buendel loest nichts aus. Ohne ihn koennte jede
# Regel unten stumpf immer klagen und trotzdem „bestehen".
index = [{"id": 1, "name": "MALATYA", "country": "TR"}]
pruefe(
    "volles Buendel, frisch erzeugt: keine Klage",
    lauf(buendel({"1": 300}), index),
    erwartet_klage=False,
)

pruefe(
    "Ort ohne Zeiten fuer heute",
    lauf(buendel({"1": -1}), index),
    erwartet_klage=True,
)

pruefe(
    "Ort reicht keine 14 Tage mehr",
    lauf(buendel({"1": 5}), index),
    erwartet_klage=True,
)

pruefe(
    "Buendel seit zu langem nicht erzeugt",
    lauf(buendel({"1": 300}, alter_tage=wache.MAX_ALTER_TAGE + 1), index),
    erwartet_klage=True,
)

# **Der Fall vom 2026-09-14.** Rutscht der Vorrat eines Ortes ganz aus dem
# Fenster, steht er nicht mehr im Buendel — eine Zaehlung innerhalb des
# Buendels sieht ihn nie wieder. Ohne den Index-Abgleich meldet dieser Fall
# nichts, obwohl ein Ort seine amtlichen Zeiten verloren hat.
pruefe(
    "Ort aus dem Index fehlt im Buendel ganz",
    lauf(buendel({"2": 300}), index + [{"id": 2, "name": "ORDU", "country": "TR"}]),
    erwartet_klage=True,
)

pruefe(
    "ohne Index-Liste bleibt die alte Zaehlung gueltig",
    lauf(buendel({"1": 300}), None),
    erwartet_klage=False,
)

print()
if GEZAEHLT["fehler"]:
    print(f"✗ {GEZAEHLT['fehler']} von {GEZAEHLT['faelle']} Faellen durchgefallen.")
    sys.exit(1)
print(f"✓ {GEZAEHLT['faelle']} Faelle, alle wie erwartet.")
