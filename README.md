# sc-unpacked-data

Données de jeu de **Star Citizen**, extraites des fichiers du jeu installé et converties en JSON.
Même format que [StarCitizenWiki/scunpacked-data](https://github.com/StarCitizenWiki/scunpacked-data) :
ce dépôt existe pour disposer des données d'un patch sans attendre.

La version du jeu correspondante est dans [`_version.json`](_version.json), et dans le message de chaque commit.

## Contenu

| Chemin | Contenu |
|---|---|
| `ships.json`, `ships/` | Vaisseaux et véhicules, avec leur loadout |
| `ship-items.json` | Composants de vaisseaux |
| `fps-items.json` | Armes, armures et équipement FPS |
| `items.json`, `items/` | Tous les objets du jeu, une fiche par objet |
| `blueprints.json`, `blueprints/` | Plans de fabrication |
| `contracts/` | Contrats et missions |
| `contracts.jsonl.xz` | Tous les contrats en un seul fichier (xz, une ligne JSON par contrat : `path` + `data`) |
| `factions/` | Factions et paliers de réputation |
| `resources/` | Minerais, récoltables, lieux de minage, denrées |
| `starmap.json`, `starmap_positions.json`, `trade_locations.json` | Carte stellaire, positions, lieux de commerce |
| `labels.json`, `manufacturers.json`, `tags.json` | Textes anglais du jeu, fabricants, tags |
| `_outils/` | Scripts et correctifs utilisés pour produire l'export |

## Fabrication

1. [unp4k](https://github.com/dolkensp/unp4k) (MIT) sort les fichiers de `Data.p4k` ;
2. `unforge`, dans la variante de [StarCitizenWiki/unp4k](https://github.com/StarCitizenWiki/unp4k), les convertit en XML ;
3. [ScDataDumper](https://github.com/octfx/ScDataDumper) (MIT, H. C. Kruse) produit les JSON, avec les correctifs de `_outils/lyra-4.10.2.patch`.

Les noms canoniques des fabricants viennent du [Star Citizen Wiki](https://starcitizen.tools) (commande `wiki:sync` de ScDataDumper).

## Avertissement

Dépôt non officiel, sans lien avec Cloud Imperium Games. Star Citizen®, Roberts Space Industries® et
Cloud Imperium® sont des marques de Cloud Imperium Rights LLC. Le contenu du jeu reste la propriété de
Cloud Imperium Games et de ses filiales ; ces données sont fournies telles quelles, à titre d'information,
sans aucune garantie d'exactitude.
