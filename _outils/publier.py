# -*- coding: utf-8 -*-
"""
publier.py — pousse export/ sur le dépôt GitHub public.

Le dépôt git vit dans depot/ et non dans export/ : extraire.py renomme export/
à chaque passage, ce qui casserait un dépôt posé dedans. Ce script recopie
export/ vers depot/ (miroir : ce qui a disparu de l'export disparaît du dépôt),
montre ce qui change, demande confirmation, puis pousse.

Usage : python publier.py          (demande confirmation)
        python publier.py --oui    (ne demande rien)
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).parent.resolve()
EXPORT = RACINE / "export"
DEPOT = RACINE / "depot"
OUTILS = RACINE / "outils"
# Scripts et correctifs recopiés dans _outils/ : la seule trace, hors de ce PC,
# de la façon dont l'export est fabriqué.
A_JOINDRE = [RACINE / "extraire.py", RACINE / "publier.py", RACINE / "EXTRAIRE_DONNEES_JEU.bat",
             RACINE / "PUBLIER.bat", OUTILS / "comparer.py", OUTILS / "Dockerfile.lyra",
             OUTILS / "lyra-4.10.2.patch"]


def git(*args, capture=False):
    r = subprocess.run(["git", "-C", str(DEPOT), *args], capture_output=capture, text=True,
                       encoding="utf-8", errors="replace")
    return r.stdout.strip() if capture else r.returncode


def stop(msg):
    print(f"\n[ARRÊT] {msg}")
    sys.exit(1)


def main():
    if not (DEPOT / ".git").is_dir():
        stop("depot/ n'est pas un dépôt git (il se crée une fois, à la première publication).")
    try:
        jeu = json.loads((EXPORT / "_version.json").read_text(encoding="utf-8"))["jeu"]
    except (OSError, ValueError, KeyError):
        stop("export/_version.json absent : lance d'abord EXTRAIRE_DONNEES_JEU.bat.")
    etiquette = f"{jeu.get('patch', '?')} · {jeu['branche']} · {jeu['version']} · {jeu['changelist']}"

    print("Copie de export/ vers depot/…")
    # robocopy /MIR : miroir. Codes de retour < 8 = réussite.
    rc = subprocess.run(["robocopy", str(EXPORT), str(DEPOT), "/MIR", "/XD", ".git", "_outils",
                         "/XF", "README.md", ".gitattributes", "_tree.json",
                         "/NFL", "/NDL", "/NJH", "/NJS", "/NP", "/MT:16"]).returncode
    if rc >= 8:
        stop(f"La copie a échoué (robocopy {rc}).")
    shutil.copyfile(OUTILS / "README_depot.md", DEPOT / "README.md")
    (DEPOT / "_outils").mkdir(exist_ok=True)
    for f in A_JOINDRE:
        if f.is_file():
            shutil.copyfile(f, DEPOT / "_outils" / f.name)

    git("add", "-A")
    resume = git("diff", "--cached", "--shortstat", capture=True)
    if not resume:
        print("Rien à publier : le dépôt est déjà à jour.")
        return
    print(f"\nVersion : {etiquette}\nChangements : {resume}")
    if "--oui" not in sys.argv:
        if input("Publier sur GitHub (dépôt PUBLIC) ? [oui/non] ").strip().lower() not in ("oui", "o"):
            print("Annulé. Rien n'a été envoyé.")
            return
    if git("commit", "-q", "-m", etiquette) != 0:
        stop("Le commit a échoué.")
    if git("push", "origin", "master") != 0:
        stop("L'envoi a échoué (connexion ? authentification GitHub ?). Le commit local est conservé.")
    print(f"\n[OK] Publié : {etiquette}")


if __name__ == "__main__":
    main()
