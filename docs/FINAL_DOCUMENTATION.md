# ElementChess — documentation fonctionnelle consolidée

## 1. Finalité

ElementChess transforme les échecs classiques en jeu de stratégie
stochastique. Les mouvements des pièces restent reconnaissables, mais le
joueur doit arbitrer entre quatre pressions : position échiquéenne, conquête
territoriale, économie de jetons et risque d'attaque repoussée.

La version Python publiée est une preuve de concept locale à deux joueurs. Son
but est de valider les règles et l'équilibrage. La version C++/SFML ajoutera les
ressources audiovisuelles, l'interface de production et le jeu en ligne.

## 2. Support de jeu

L'échiquier 8×8 est projeté sur une grille mixte 17×17. Une cellule sur deux
sert aux pièces ; les cellules intermédiaires portent le système territorial.

| Objet | Définition |
|---|---|
| Cellule de jeu | Reçoit une pièce et son orientation ; ne reçoit ni nombre ni élément territorial |
| Cellule terrain | Porte un état élémentaire et, si applicable, une valeur de 1 à 5 |
| Parcelle | Zone locale 5×5 utilisée pour la complétion numérique et la capture |
| Bande limite | Couronne extérieure sans numérotation, intégrée aux relations élémentaires |

Les neuf parcelles forment le centre 15×15. La projection d'une case d'échecs
`(x, y)` est `(2x+1, 2y+1)`.

## 3. Informations territoriales

Chaque cellule terrain possède deux couches indépendantes :

- une valeur éventuelle de `1` à `5` ;
- l'un des huit éléments : Eau, Feu, Vent, Bois, Terre, Glace, Magmat ou
  Foudre.

Les valeurs sont résolues localement dans chaque parcelle. Les éléments sont
évalués sur la grille globale. Les deux listes ne doivent jamais être
permutées par la même opération.

## 4. Éléments et états

Un élément peut être neutre, actif ou passif. L'état provient de l'interstice
et possède une durée limitée.

| État | Effet de référence |
|---|---|
| Neutre | contribution nulle |
| Actif | contribution positive de niveau 1, 2 ou 3 |
| Passif | contribution complémentaire négative de niveau 1, 2 ou 3 |

Les contributions de référence sont `±50`, `±100` et `±150`. Elles modifient
la puissance sans changer la géométrie des déplacements.

## 5. Déroulement d'une ronde

Chaque joueur réalise successivement :

1. placement, conservation ou recyclage autorisé de jetons ;
2. sélection et déplacement légal d'une pièce ;
3. résolution d'un combat éventuel ;
4. orientation de la pièce déplacée ;
5. verrouillage de cette orientation.

Après les deux joueurs vient l'interstice : tirage élémentaire, complétions
liées aux orientations, attribution des jetons, mise à jour des états et
évaluation de la Balance Map.

## 6. Règles échiquéennes conservées

- mouvements propres à chaque pièce ;
- obstruction des pièces à déplacement linéaire ;
- interdiction de laisser son roi en échec ;
- seuls les mouvements qui suppriment un échec sont autorisés ;
- promotion automatique d'un pion en dame sur la dernière ligne ;
- mouvement défensif roi-tour lorsque ses conditions particulières sont
  réunies ;
- échec et mat terminal.

Une attaque défensive repoussée alors que le roi reste en échec provoque la
défaite immédiate du défenseur.

## 7. Résolution des combats

À puissance égale, la probabilité de référence d'une attaque repoussée est
`1/3`. L'écart attaque-défense la fait varier dans un intervalle borné :

`P(rejet) = borne(1/3 + (défense - attaque) / 900, 0,12, 0,65)`.

La probabilité de capture vaut `1 - P(rejet)`. La seed et les événements
aléatoires doivent être enregistrés pour permettre une relecture déterministe.

## 8. Complétion et capture territoriale

Les nombres admissibles d'une cellule sont ceux qui n'apparaissent pas encore
sur ses segments numériques locaux. Une cellule de jeu sépare les segments et
n'est jamais considérée comme une valeur.

Lorsqu'un élément tiré correspond à l'orientation d'une pièce qui vise une
cellule terrain, les complétions concernées bénéficient au joueur qui occupe
la parcelle. En occupation commune, le départage applique successivement :

1. le nombre de pièces présentes ;
2. le nombre de jetons de chaque camp ;
3. aucune attribution automatique si l'égalité persiste.

Une parcelle capturée est figée et sort définitivement des permutations
numériques.

## 9. Conditions terminales

| Condition | Conséquence |
|---|---|
| Échec et mat | victoire de l'adversaire |
| Trois parcelles capturées et alignées | victoire territoriale |
| Seuil terminal de 21 jetons validé | victoire économique |
| Trois attaques d'un joueur repoussées | défaite de l'attaquant |
| Défense repoussée sans résolution de l'échec | défaite du défenseur |

Après une fin de partie, l'interface annonce le gagnant, le perdant et la
cause, puis propose de recommencer ou de quitter.

## 10. Modèle fractal universel étendu

Le modèle applique un même patron à plusieurs niveaux : support invariant,
liste d'entités, état, opération et transition. Il sert aux cellules, aux
parcelles, au plateau et à la trajectoire de partie. La géométrie reste stable ;
les nombres, éléments, pièces et états forment les données évolutives.

Cette séparation doit devenir la frontière du moteur C++ : aucune règle ne
doit dépendre d'un sprite, d'un son, d'une fenêtre ou d'une API réseau.

## 11. Balance Map

La Balance Map ajoute à l'état horizontal du plateau un axe temporel composé
d'un cycle et d'un générateur. Au tour `N`, elle compare le scénario sans
intervention et les permutations admissibles projetées à `N+4`.

- les permutations numériques portent uniquement sur une parcelle 5×5 ;
- les permutations élémentaires portent sur une ligne ou colonne globale ;
- toute ligne élémentaire comportant une discontinuité non territoriale est
  entièrement exclue ;
- une parcelle capturée est exclue des cycles numériques ;
- une parcelle bloquée ne doit pas rester sans correction admissible pendant
  plus de trois observations consécutives.

Le système distingue début, milieu et fin à partir d'un score d'avancement
mesuré, sans numéro de tour fixe. Il observe au début, prévient surtout les
blocages au milieu et réduit ses interventions en fin de partie.

## 12. Invariants obligatoires

- aucune donnée territoriale sur une cellule de jeu ;
- aucun mouvement laissant son propre roi en échec ;
- aucune simulation modifiant la partie réelle ;
- aucune permutation partielle d'une ligne élémentaire exclue ;
- aucune permutation numérique d'une parcelle capturée ;
- somme des probabilités d'un combat égale à `1` ;
- même seed et même journal d'actions, même résultat ;
- affichage sans influence sur les règles ;
- partie classée validée par une autorité et non par un client seul.

## 13. Statut de la spécification

Les règles ci-dessus constituent la référence du POC validé. Les paramètres
statistiques restent calibrables. Toute règle nouvelle doit être ajoutée ici,
associée à un événement de domaine et à un test automatisé avant d'être
considérée comme implémentée.
