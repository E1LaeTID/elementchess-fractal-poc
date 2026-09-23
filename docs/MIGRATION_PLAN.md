# Plan d'implémentation

| Étape | Livrable | Critère de sortie |
|---:|---|---|
| 0 | Spécification gelée du POC | règles et invariants reliés aux tests Python |
| 1 | `elementchess_core` C++ | types, commandes et événements compilent sans SFML |
| 2 | Parité des règles | mêmes scénarios et seeds, mêmes états finaux Python/C++ |
| 3 | Client SFML minimal | plateau, pièces, sélection et HUD depuis un snapshot |
| 4 | Pipeline de ressources | manifeste, cache, fallback, crédits et packaging |
| 5 | UX complète | scènes, animations, audio, accessibilité, résultat/revanche |
| 6 | Replays | journal versionné et vérification d'empreintes |
| 7 | Réseau hors Steam | transport factice et parties automatisées client/autorité |
| 8 | Steamworks | identité, lobby, invitations et transport Steam |
| 9 | Matchmaking classé | Glicko-2, files, abandon, reconnexion et observabilité |
| 10 | Bêta fermée | télémétrie consentie, crash reports et recalibrage |

## Règles de migration

1. ne pas réécrire l'interface avant les règles ;
2. ne pas intégrer Steamworks dans le moteur ;
3. ne pas utiliser les statistiques détaillées comme bonus de classement ;
4. ne pas supprimer le POC Python avant la parité des scénarios ;
5. ne pas rendre une file classée disponible sans autorité et replay ;
6. ne pas intégrer une ressource sans origine, licence et fallback.

## Premier jalon concret

Le premier jalon n'est pas une reproduction visuelle. C'est un exécutable de
test C++ capable de charger une seed, appliquer une suite de commandes et
produire le même hash d'état que Python. SFML est branché seulement après ce
test de parité.
