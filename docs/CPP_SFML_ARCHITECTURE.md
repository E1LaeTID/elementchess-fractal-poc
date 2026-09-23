# Architecture cible C++/SFML

## 1. Choix de base

- C++17 minimum ;
- CMake et cibles modernes ;
- SFML 3.1 pour fenêtre, entrées, rendu et audio ;
- moteur de règles sans dépendance à SFML ;
- adaptateur Steamworks optionnel, compilé séparément ;
- sérialisation versionnée pour sauvegardes, réseau et replays.

## 2. Découpage

| Couche | Responsabilité | Dépendances autorisées |
|---|---|---|
| `domain` | types, coordonnées, pièces, parcelles, événements | bibliothèque standard |
| `rules` | mouvements, combats, territoires, fins de partie | `domain` |
| `balance` | phases, simulations N+4, permutations | `domain`, `rules` |
| `application` | commandes, orchestration, snapshots | couches métier |
| `render_sfml` | scènes, caméra, animations, HUD | SFML, `application` en lecture |
| `assets` | manifestes, cache, chargement et fallback | SFML pour les ressources graphiques |
| `online` | protocole, lobby, synchronisation, replay | contrats d'application |
| `platform_steam` | Steamworks, lobbies, identité, transport | Steamworks, `online` |

Le rendu reçoit un `GameSnapshot` immuable et produit uniquement des intentions
utilisateur. Le moteur valide ensuite ces intentions et émet des événements.

## 3. Boucle d'application

1. collecter les événements SFML ;
2. traduire l'entrée en commande métier ;
3. valider et appliquer la commande ;
4. publier les événements de domaine ;
5. mettre à jour animations et audio ;
6. dessiner le dernier snapshot interpolé.

La simulation métier utilise un pas logique indépendant de la fréquence
d'affichage. Une partie réseau ne doit jamais dépendre du nombre d'images par
seconde.

## 4. Gestion de l'affichage

L'interface devient un empilement de couches :

1. fond et ambiance ;
2. support 17×17 ;
3. états territoriaux et élémentaires ;
4. pièces ;
5. surbrillances légales ;
6. effets et animations ;
7. interface et fenêtres modales.

Les surbrillances de territoire sont dessinées avant les pièces avec une
opacité limitée. Aucun texte ne recouvre une pièce. Les informations détaillées
apparaissent dans un panneau ou une infobulle contextuelle.

## 5. Ressources externes

Les chemins ne doivent pas être écrits dans le code. Un manifeste versionné
associe des identifiants stables aux fichiers :

```json
{
  "schema": 1,
  "textures": { "piece.white.king": "textures/pieces/white_king.png" },
  "fonts": { "ui.regular": "fonts/ui_regular.ttf" },
  "sounds": { "combat.rejected": "audio/combat_rejected.ogg" },
  "music": { "match.default": "music/match_default.ogg" }
}
```

Le `ResourceManager` charge une ressource une seule fois, fournit un fallback
visible en cas d'absence et journalise l'erreur. La propriété intellectuelle et
la licence de chaque ressource doivent être enregistrées dans
`assets/CREDITS.json`.

## 6. Scènes prévues

- amorçage et validation des ressources ;
- menu principal ;
- partie locale ;
- recherche de partie ;
- lobby ;
- partie en ligne ;
- résultat et revanche ;
- options, accessibilité et commandes ;
- relecture d'une partie.

## 7. Contrats à porter depuis Python

L'ordre recommandé est : types de domaine, projection 8×8/17×17, mouvements,
échec et mat, jetons, complétion, orientation, combat, interstice, cycles,
Balance Map, puis interface. Chaque module C++ doit reprendre les mêmes cas de
test avant suppression éventuelle de son équivalent Python.

## 8. Reproductibilité

Chaque partie possède : version des règles, seed initiale, séquence numérotée
de commandes, événements produits et empreinte périodique de l'état. Un replay
rejoue les commandes dans le moteur ; il ne sauvegarde pas une vidéo.
