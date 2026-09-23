# Événements, réseau et matchmaking

## 1. Autorité de partie

Une partie locale utilise le moteur directement. Une partie en ligne classée
utilise une autorité logique qui valide les commandes, possède la seed et
produit le journal officiel. Le client SFML reste responsable de l'affichage,
des entrées et de la prédiction visuelle, jamais du résultat classé.

Pour Steam, les lobbies servent à découvrir et réunir les joueurs ; le trafic
de partie utilise un transport séparé. Les interfaces `ILobbyService` et
`ITransport` évitent de lier le moteur à Steamworks et permettent un mode local
ou de test sans Steam.

## 2. Événements de domaine

Les événements sont versionnés et ordonnés. Exemples :

- `MatchCreated`, `PlayerJoined`, `MatchStarted` ;
- `TokenPlaced`, `PieceMoved`, `PieceOriented` ;
- `CombatResolved`, `AttackRejected`, `PieceCaptured` ;
- `TerrainCompleted`, `TerrainCaptured` ;
- `PermutationScheduled`, `PermutationApplied` ;
- `KingChecked`, `MatchEnded`, `RatingUpdated`.

Chaque message réseau porte `matchId`, `sequence`, `rulesVersion` et, si
nécessaire, `stateHash`. Une rupture de séquence déclenche une resynchronisation
par snapshot signé par l'autorité.

## 3. Mesure de compétence

Le classement recommandé est Glicko-2 :

- `rating` estime le niveau ;
- `deviation` mesure l'incertitude ;
- `volatility` mesure la variabilité récente.

Un nouveau joueur commence avec une forte incertitude. Les premières parties
le repositionnent plus vite ; un joueur établi évolue plus lentement. Les
parties abandonnées et déconnexions sont traitées par une politique distincte,
mais ne peuvent pas être ignorées pour éviter la manipulation.

Le résultat principal reste victoire, nul ou défaite. Les voies de victoire
ne modifient pas directement le classement général : sinon le système
encouragerait artificiellement une stratégie. Elles alimentent des indicateurs
non classants permettant de décrire le profil du joueur :

- pression échiquéenne ;
- maîtrise territoriale ;
- économie de jetons ;
- gestion du risque stochastique.

## 4. Qualité d'une paire

Pour deux profils `a` et `b`, le service minimise un coût composé :

`coût = écart_conservateur + incertitude + latence + répétition + incompatibilité`.

L'estimation conservatrice est `rating - 2 × deviation`. Les contraintes
dures sont évaluées avant le score : version des règles, région autorisée,
mode, contrôle d'intégrité et disponibilité.

La fenêtre de recherche s'élargit avec l'attente :

- priorité à un niveau proche pendant les premières secondes ;
- élargissement progressif du niveau et de la région ;
- plafond explicite au-delà duquel le joueur choisit d'attendre ou d'accepter
  une partie non classée.

## 5. Files séparées

- découverte/non classée ;
- classée ;
- partie privée par invitation ;
- test de règles expérimentales ;
- revanche, sans garantie de classement si elle favorise les arrangements.

Les versions différentes des règles ne partagent jamais une file classée.

## 6. Intégrité

- journal complet des commandes et seeds ;
- validation de chaque mouvement par l'autorité ;
- limite de temps côté autorité ;
- détection des abandons répétés ;
- idempotence des commandes réseau ;
- résultat classé appliqué une seule fois ;
- reprise après reconnexion depuis le dernier état confirmé ;
- statistiques d'équilibrage anonymisées et séparées des données personnelles.

## 7. Mesures d'exploitation

Le service doit suivre : temps d'attente, écart de niveau, taux de parties
terminées, abandons, reconnexions, durée, voie de victoire, fréquence des
attaques repoussées et activation des cycles. Ces mesures servent à évaluer la
qualité du matchmaking et du jeu, pas à modifier secrètement le résultat d'une
partie active.
