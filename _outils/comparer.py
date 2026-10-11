# -*- coding: utf-8 -*-
"""Compare deux exports au format scunpacked-data (référence vs le nôtre).

Usage : python comparer.py <reference> <export>

Ne juge pas les valeurs (un patch en change) : vérifie que la FORME est la
même — mêmes fichiers, mêmes volumes, mêmes clés — et liste ce qui est apparu
ou a disparu, pour qu'un export tronqué ne passe jamais pour un patch.
"""
import json
import sys
from pathlib import Path

FICHIERS = ["ships.json", "ship-items.json", "fps-items.json", "items.json",
            "blueprints.json", "starmap.json", "starmap_positions.json",
            "labels.json", "manufacturers.json", "tags.json", "trade_locations.json",
            "resources/resources.json", "resources/locations.json",
            "resources/commodities.json"]
DOSSIERS = ["blueprints", "contracts", "factions", "items", "ships", "resources"]


def charger(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as exc:
        return exc


def taille(d):
    return len(d) if isinstance(d, (list, dict)) else "?"


def cles(d):
    """Clés du premier niveau des entrées (liste de dicts ou dict de dicts)."""
    if isinstance(d, dict):
        d = list(d.values())
    out = set()
    for e in (d or [])[:500]:
        if isinstance(e, dict):
            out |= set(e)
    return out


def noms(d):
    if not isinstance(d, list):
        return set()
    out = set()
    for e in d:
        if isinstance(e, dict):
            n = e.get("ClassName") or e.get("className") or e.get("Name") or e.get("name") or e.get("uuid")
            if isinstance(n, str):
                out.add(n)
    return out


def main(ref, exp):
    ref, exp = Path(ref), Path(exp)
    print(f"{'fichier':34} {'réf':>8} {'nôtre':>8}  écart")
    for nom in FICHIERS:
        a, b = charger(ref / nom), charger(exp / nom)
        if isinstance(b, Exception):
            print(f"{nom:34} {taille(a):>8} {'ABSENT':>8}  !!! {type(b).__name__}")
            continue
        if isinstance(a, Exception):
            print(f"{nom:34} {'absent':>8} {taille(b):>8}  (nouveau)")
            continue
        ka, kb = cles(a), cles(b)
        note = []
        if ka - kb:
            note.append(f"clés perdues {sorted(ka - kb)[:6]}")
        if kb - ka:
            note.append(f"clés nouvelles {sorted(kb - ka)[:6]}")
        na, nb = noms(a), noms(b)
        if na and nb:
            note.append(f"+{len(nb - na)} / -{len(na - nb)} entrées")
        print(f"{nom:34} {taille(a):>8} {taille(b):>8}  {' ; '.join(note)}")
    print()
    for d in DOSSIERS:
        fa = {p.relative_to(ref / d).as_posix() for p in (ref / d).rglob("*.json")} if (ref / d).is_dir() else set()
        fb = {p.relative_to(exp / d).as_posix() for p in (exp / d).rglob("*.json")} if (exp / d).is_dir() else set()
        print(f"{d + '/':34} {len(fa):>8} {len(fb):>8}  +{len(fb - fa)} / -{len(fa - fb)} fichiers")
    for nom in ("ships.json", "ship-items.json", "fps-items.json"):
        a, b = charger(ref / nom), charger(exp / nom)
        if isinstance(a, list) and isinstance(b, list):
            plus, moins = sorted(noms(b) - noms(a)), sorted(noms(a) - noms(b))
            print(f"\n{nom} — apparus ({len(plus)}) : {plus[:25]}")
            print(f"{nom} — disparus ({len(moins)}) : {moins[:25]}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
