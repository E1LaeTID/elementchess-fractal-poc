# Dictionnaire statistique adaptatif de la balance map

Le dictionnaire ne contient plus de limites numériques fixes pour le début, le
milieu et la fin. Il décrit les variables, les estimateurs et la règle de
décision permettant d'apprendre ces limites sur les parties de référence.

## 1. Géométrie des neuf terrains

Les quatre familles observées dans le cahier des charges sont reconnues par
leur géométrie, et non par leur position :

| Famille | Occurrences | Lignes complètes | Colonnes complètes |
|---|---:|---:|---:|
| A | 1 | 3 | 3 |
| B | 2 | 3 | 2 |
| C | 2 | 2 | 3 |
| D | 4 | 2 | 2 |

Le nombre de jetons requis, de cases à double contrainte et de cases à
contrainte simple est recalculé depuis la grille. Une modification future du
support ne rendra donc pas le dictionnaire faux.

Pour un terrain `z` dans l'état `s`, la probabilité de complétion au tirage `n`
est conditionnelle :

\[
P_z(n\mid s)=P\left(\bigcap_{c\in C_z(s)}
\{X_c\in L_c(s)\}\;\middle|\;5\text{ jetons au premier tirage, puis }2\right),
\]

où `C_z(s)` est l'ensemble des cases numériques encore libres et `L_c(s)` la
liste des valeurs légales de la case. Une parcelle capturée est retirée de
`C_z`, des mesures et des cycles numériques.

## 2. Limites de phase apprises

Chaque état produit un vecteur d'avancement : rang empirique du tour,
occupation territoriale, remplissage des terrains non capturés, réduction du
matériel, attaques repoussées et saturation des stocks. Après normalisation :

\[
G(s)=\sum_i w_i f_i(s),\qquad \sum_i w_i=1.
\]

Les poids sont calibrés sur les trajectoires terminées. Les deux limites sont
les terciles empiriques des scores observés :

\[
L_1=Q_{1/3}(G),\qquad L_2=Q_{2/3}(G).
\]

Ainsi, début, milieu et fin restent trois zones relatives, mais `L1` et `L2`
ne correspondent à aucun tour fixé. Ils sont réestimés entre les parties de
test, jamais pendant une partie active. La phase d'une partie ne régresse pas.

## 3. Décision contrefactuelle à N+4

Au tour `N`, le contrôleur construit :

- un témoin `H0` : évolution à `N+4` sans permutation ;
- un scénario par permutation numérique admissible ;
- un scénario par permutation élémentaire admissible.

Chaque scénario mesure à `N+4` le risque de blocage, les quatre pressions de
fin de partie, l'écart d'avantage et l'indice de dilemme territoire/position.
Une permutation n'est admissible que si elle améliore le blocage ou le dilemme
sans inverser artificiellement l'avantage déjà acquis. Sinon, `H0` gagne et
aucune permutation n'est appliquée.

Le choix porte sur des intervalles de confiance. Tant que l'échantillon est
insuffisant, le système observe et journalise mais ne régule pas.

## 4. Lois utilisées

- événements binaires, dont attaque repoussée : modèle bêta-binomial ;
- complétion d'un terrain : simulation conditionnelle des listes légales ;
- comparaison multivariable à `N+4` : bootstrap des trajectoires ;
- valeurs `1..5` : distribution conditionnelle au stock restant et aux listes
  légales, jamais cinq pourcentages constants ;
- éléments actifs/passifs : estimation conditionnelle à la phase, à la
  géométrie de confrontation et à la signature élémentaire.

Cette structure sépare donc une **loi de référence** d'une **valeur apprise**.
Le dépôt peut publier la méthode immédiatement et compléter progressivement
les distributions avec les tests de la version console.
