# -*- coding: utf-8 -*-
"""
extraire.py — fabrique l'export « scunpacked » depuis le Star Citizen installé.

Chaîne (la même que celle du wiki, rejouée chez nous) :
  1. unp4k     : sort les .xml / .ini / .socpak / .dcb de Data.p4k
  2. unforge   : convertit en XML lisible (build du fork StarCitizenWiki, le
                 seul qui écrit le Game2.xml dont l'étape 3 a besoin)
  3. ScDataDumper (Docker) : XML -> JSON au format scunpacked-data

Usage :
  python extraire.py                 tout, depuis le jeu installé (LIVE)
  python extraire.py --sans-extraction   réutilise le dossier import/ existant
  python extraire.py --p4k "D:\\...\\Data.p4k"

Rien n'est écrit dans le dossier du jeu. Le résultat arrive dans
export-<version>/ et ne remplace export/ que s'il passe les contrôles.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

RACINE = Path(__file__).parent.resolve()
OUTILS = RACINE / "outils"
UNP4K = OUTILS / "unp4k" / "publish" / "unp4k.exe"
UNFORGE = OUTILS / "unforge-wiki" / "unforge.cli.exe"
DUMPER = OUTILS / "ScDataDumper"
IMPORT = RACINE / "import"
EXPORT = RACINE / "export"
IMAGE_BASE = "scdatadumper-scdatadumper"
IMAGE = "lyra-scdatadumper"
VOL_IMPORT = "lyra-sc-import"
VOL_EXPORT = "lyra-sc-export"
P4K_DEFAUT = Path(r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\Data.p4k")
ESPACE_MIN_GO = 30

# Planchers : un export qui s'effondre (format du jeu changé, étape ratée) ne
# doit jamais passer pour un patch. Valeurs 4.10.2 entre parenthèses.
PLANCHERS = {
    "ships.json": 300,                   # (331)
    "ship-items.json": 5000,             # (5597)
    "fps-items.json": 5000,              # (5542)
    "blueprints.json": 1400,             # (1618)
    "starmap.json": 1900,                # (2119)
    "labels.json": 80000,                # (90946)
    "manufacturers.json": 100,           # (141)
    "resources/resources.json": 450,     # (557)
    "resources/commodities.json": 150,   # (206)
    "resources/locations.json": 50,      # (66)
}
PLANCHERS_DOSSIERS = {"contracts": 4500, "factions": 60}   # (5153, 75)


def dire(msg=""):
    print(msg, flush=True)


def etape(titre):
    dire(f"\n=== {titre} ({time.strftime('%H:%M:%S')}) ===")


def stop(msg):
    dire(f"\n[ARRÊT] {msg}")
    sys.exit(1)


def lancer(cmd, journal=None, cwd=None):
    """Exécute, sortie vers un fichier journal (ces outils sont très bavards)."""
    if journal:
        with open(journal, "w", encoding="utf-8", errors="replace") as f:
            return subprocess.run(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT).returncode
    return subprocess.run(cmd, cwd=cwd).returncode


def docker(*args, journal=None):
    return lancer(["docker", *args], journal=journal)


def version_jeu(p4k: Path) -> dict:
    try:
        d = json.loads(p4k.with_name("build_manifest.id").read_text(encoding="utf-8")).get("Data", {})
        return {"branche": d.get("Branch"), "version": d.get("Version"),
                "changelist": d.get("RequestedP4ChangeNum")}
    except (OSError, ValueError):
        return {}


# ── Étapes ─────────────────────────────────────────────────────────────

def verifier(p4k: Path, extraction: bool):
    etape("Vérifications")
    if extraction:
        if not p4k.is_file():
            stop(f"Data.p4k introuvable : {p4k}\n  Indique-le avec --p4k \"chemin\\Data.p4k\"")
        for exe in (UNP4K, UNFORGE):
            if not exe.is_file():
                stop(f"Outil manquant : {exe}")
        libre = shutil.disk_usage(RACINE).free / 1e9
        if libre < ESPACE_MIN_GO:
            stop(f"Espace disque insuffisant : {libre:.0f} Go libres, {ESPACE_MIN_GO} Go nécessaires.")
        dire(f"  Jeu      : {p4k}")
        dire(f"  Disque   : {libre:.0f} Go libres")
    if subprocess.run(["docker", "info"], capture_output=True).returncode != 0:
        stop("Docker ne répond pas. Lance Docker Desktop, attends qu'il soit prêt, puis relance.")
    dire("  Docker   : prêt")


def extraire(p4k: Path):
    etape("1/4 — Extraction des fichiers du jeu (≈ 2 min)")
    if IMPORT.exists():
        dire("  Nettoyage de l'ancienne extraction…")
        shutil.rmtree(IMPORT)
    IMPORT.mkdir()
    for motif in ("*.xml", "*.ini", "*.socpak", "*.dcb"):
        dire(f"  {motif}")
        rc = lancer([str(UNP4K), str(p4k), motif], journal=RACINE / "journal_unp4k.log", cwd=IMPORT)
        if rc != 0:
            stop(f"unp4k a échoué sur {motif} (voir journal_unp4k.log).")
    etape("2/4 — Conversion en XML lisible (≈ 10-20 min, rien ne s'affiche)")
    lancer([str(UNFORGE), "."], journal=RACINE / "journal_unforge.log", cwd=IMPORT)
    g2 = IMPORT / "Data" / "Game2.xml"
    if not g2.is_file() or g2.stat().st_size < 500_000_000:
        stop("Game2.xml absent ou trop petit : la conversion a échoué (voir journal_unforge.log).")
    dire(f"  Game2.xml : {g2.stat().st_size / 1e9:.1f} Go")


def image():
    if subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True).returncode == 0:
        return
    etape("Construction de l'image Docker (une seule fois, quelques minutes)")
    if docker("build", "-q", "-t", IMAGE_BASE, str(DUMPER)) != 0:
        stop("Construction de l'image ScDataDumper échouée.")
    if docker("build", "-q", "-f", str(OUTILS / "Dockerfile.lyra"), "-t", IMAGE, str(OUTILS)) != 0:
        stop("Construction de l'image lyra-scdatadumper échouée.")


def generer():
    etape("3/4 — Copie dans Docker (≈ 10 min) puis génération des JSON (≈ 5 min)")
    # Volumes neufs : un cache laissé par un essai précédent est réutilisé sans
    # être refait, et l'export sort alors incomplet sans le dire.
    for vol in (VOL_IMPORT, VOL_EXPORT):
        subprocess.run(["docker", "volume", "rm", "-f", vol], capture_output=True)
        subprocess.run(["docker", "volume", "create", vol], capture_output=True)
    rc = docker("run", "--rm", "-v", f"{IMPORT}:/src:ro", "-v", f"{VOL_IMPORT}:/dst", "alpine", "sh", "-c",
                "cd /src && tar cf - --exclude=Game2.dcb Data Engine | (cd /dst && tar xf -) && chmod -R a+rwX /dst")
    if rc != 0:
        stop("Copie des données dans le volume Docker échouée.")
    dire("  Copie terminée, génération…")
    rc = docker("run", "--rm", "-v", f"{VOL_IMPORT}:/var/www/html/import",
                "-v", f"{VOL_EXPORT}:/var/www/html/export", "-w", "/var/www/html", IMAGE, "sh", "-c",
                "php cli.php wiki:sync && php cli.php generate:cache import --overwrite"
                " && php cli.php load:data import export --overwrite",
                journal=RACINE / "journal_dumper.log")
    if rc != 0:
        fin = (RACINE / "journal_dumper.log").read_text(encoding="utf-8", errors="replace")
        fatal = [l for l in fin.replace("\r", "\n").splitlines() if "Fatal" in l or "Uncaught" in l]
        stop("ScDataDumper a planté — souvent une nouveauté du patch qu'il ne gère pas encore.\n  "
             + (fatal[-1][-300:] if fatal else "voir journal_dumper.log"))


def sortir(dest: Path):
    etape("4/4 — Récupération de l'export et contrôles")
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir()
    archive = RACINE / "_export.tar"
    with open(archive, "wb") as f:
        rc = subprocess.run(["docker", "run", "--rm", "-v", f"{VOL_EXPORT}:/e", "alpine",
                             "tar", "cf", "-", "-C", "/e", "."], stdout=f).returncode
    if rc != 0:
        stop("Récupération de l'export échouée.")
    shutil.unpack_archive(str(archive), str(dest), "tar")
    archive.unlink()


def controler(dest: Path) -> list:
    pb = []
    for nom, mini in PLANCHERS.items():
        try:
            n = len(json.loads((dest / nom).read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pb.append(f"{nom} : absent ou illisible")
            continue
        dire(f"  {nom:30} {n:>7}")
        if n < mini:
            pb.append(f"{nom} : {n} entrées, plancher {mini}")
    for nom, mini in PLANCHERS_DOSSIERS.items():
        n = sum(1 for _ in (dest / nom).rglob("*.json")) if (dest / nom).is_dir() else 0
        dire(f"  {nom + '/':30} {n:>7}")
        if n < mini:
            pb.append(f"{nom}/ : {n} fichiers, plancher {mini}")
    # Deux défauts déjà rencontrés, silencieux tous les deux.
    try:
        # Sans la synchro du wiki, les fabricants sortent en code brut du jeu
        # (« AEG », « MIS ») au lieu du code canonique (« AEGS », « MISC »).
        # (Les ~1 770 peintures sans fabricant sont normales : le wiki en a autant.)
        codes = {m.get("Code") for m in json.loads((dest / "manufacturers.json").read_text(encoding="utf-8"))}
        if not {"AEGS", "MISC"} <= codes:
            pb.append("fabricants en code brut : la synchro du wiki (wiki:sync) a échoué ?")
        fps = (dest / "fps-items.json").read_text(encoding="utf-8")
        if "BarrelAttachment" not in fps:
            pb.append("aucun canon d'arme classé dans fps-items.json (correctif de classement perdu ?)")
    except (OSError, ValueError):
        pass
    return pb


def regrouper_contrats(dest: Path) -> int:
    """Écrit contracts.jsonl.xz : tous les fichiers de contracts/ en un seul.

    LYRA lisait les contrats un par un (5 000 requêtes en rafale, dont GitHub
    refuse toujours quelques-unes). Ici, une ligne par contrat :
        {"path": "contracts/….json", "data": <contenu du fichier, tel quel>}
    Les fichiers individuels restent publiés, en repli.

    xz et non zip : les contrats se ressemblent énormément, et seule une
    compression « d'un bloc » en profite — 235 Mo deviennent ~3 Mo, contre
    55 Mo en zip (au-dessus de la taille conseillée par GitHub).
    Ordre trié : un export inchangé donne le même fichier, donc le même SHA git."""
    import lzma
    fichiers = sorted((dest / "contracts").rglob("*.json"))
    lignes = []
    for f in fichiers:
        # Relu puis réécrit en compact : garantit UNE ligne par contrat, quelle
        # que soit la mise en forme du fichier d'origine.
        ligne = json.dumps({"path": f.relative_to(dest).as_posix(),
                            "data": json.loads(f.read_bytes())},
                           ensure_ascii=False, separators=(",", ":"))
        lignes.append(ligne.encode("utf-8") + bytes([10]))
    cible = dest / "contracts.jsonl.xz"
    cible.write_bytes(lzma.compress(b"".join(lignes), preset=6))
    dire(f"  contracts.jsonl.xz             {len(fichiers):>7} contrats, {cible.stat().st_size / 1e6:.1f} Mo")
    return len(fichiers)


def main():
    ap = argparse.ArgumentParser(description="Fabrique l'export scunpacked depuis le jeu installé.")
    ap.add_argument("--p4k", type=Path, default=P4K_DEFAUT)
    ap.add_argument("--sans-extraction", action="store_true",
                    help="réutilise import/ (étapes 1 et 2 sautées)")
    a = ap.parse_args()
    debut = time.time()

    verifier(a.p4k, not a.sans_extraction)
    jeu = version_jeu(a.p4k)
    nom = f"{jeu.get('version', 'inconnue')}-{jeu.get('changelist', '0')}"
    dire(f"  Version  : {jeu.get('branche')} · {nom}")

    if not a.sans_extraction:
        extraire(a.p4k)
    elif not (IMPORT / "Data" / "Game2.xml").is_file():
        stop("--sans-extraction demandé mais import/Data/Game2.xml n'existe pas.")
    image()
    generer()
    dest = RACINE / f"export-{nom}"
    sortir(dest)
    pb = controler(dest)
    if pb:
        dire("\n[REFUSÉ] L'export est suspect, export/ n'a PAS été remplacé :")
        for p in pb:
            dire(f"  - {p}")
        dire(f"  Il reste consultable dans {dest.name}/")
        sys.exit(2)

    regrouper_contrats(dest)
    (dest / "_version.json").write_text(json.dumps(
        {"jeu": jeu, "genere_le": time.strftime("%Y-%m-%d %H:%M:%S"),
         "outil": "unp4k + unforge (fork StarCitizenWiki) + ScDataDumper (octfx) + correctifs LYRA"},
        ensure_ascii=False, indent=1), encoding="utf-8")
    ancien = RACINE / "export-precedent"
    if EXPORT.exists():
        if ancien.exists():
            shutil.rmtree(ancien)
        EXPORT.rename(ancien)
    dest.rename(EXPORT)
    if ancien.exists():
        dire("\n— Comparaison avec l'export précédent —")
        lancer([sys.executable, str(OUTILS / "comparer.py"), str(ancien), str(EXPORT)])
    dire(f"\n[OK] Export {nom} prêt dans export/ — {int((time.time() - debut) / 60)} min.")
    dire("     L'ancien est gardé dans export-precedent/. import/ peut être supprimé pour libérer ~11 Go.")


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    main()
