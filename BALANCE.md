# Formules de jeu et d'équilibrage

Cette annexe rassemble les formules du prototype. Elle sépare les domaines
numérique, élémentaire, échiquéen et statistique afin qu'une modification de
l'un d'eux ne change pas implicitement les autres.

## 1. Domaines de calcul

| Domaine | Échelle | Rôle |
|---|---|---|
| Échiquéen | grille 17×17 | déplacements, échec, mat et orientation |
| Numérique | parcelle locale 5×5 | jetons 1 à 5 et capture territoriale |
| Élémentaire | lignes et colonnes globales | états actifs/passifs et combats |
| Statistique | trajectoire de partie | phases, blocages et permutations à `N+4` |

Une cellule de jeu interrompt une ligne numérique. Une ligne ou colonne
élémentaire comportant une discontinuité autre qu'une cellule terrain est
entièrement exclue d'un cycle : aucun de ses segments n'est permuté.

## 2. Puissances d'attaque et de défense

Pour une ligne de rang `y` sur le support 17×17 :

\[
C(y)=50|y-8|,\qquad LP(y)=100+C(y).
\]

La ligne centrale vaut donc `100` et les lignes arrière atteignent `500`.
L'offset garantit une puissance minimale de `100`.

Pour une liste élémentaire utile `L*`, la contribution signée est :

\[
E(L)=\left\lceil
\frac{1}{|L^*|}\sum_{e\in L^*} s(e)\,\ell(e)\,50
\right\rceil,
\]

où `s(e)` vaut `+1` à l'état actif, `−1` à l'état passif et `0` à l'état
neutre ; `ℓ(e)` vaut 1, 2 ou 3.

La puissance d'une pièce est ensuite bornée :

\[
P=\max\left(100,
\operatorname{moyenne}(LP_i+E_i)+20V_p+B_o+5S_n
\right).
\]

`Vp` est la valeur propre de la pièce, `Bo` le bonus d'orientation et `Sn` la
contribution numérique applicable. Les facteurs de ligne sont calculés avant
la moyenne et ne sont jamais multipliés par les nombres territoriaux.

## 3. Trois géométries de confrontation

| Géométrie | Défense | Attaque |
|---|---|---|
| Sens d'avancée par défaut | trois éléments communs sur la ligne et complémentaire du défenseur | voisins diagonaux de l'attaquant, élément commun exclu |
| Sens opposé | relations inversées selon l'orientation du joueur | même règle locale, dans le sens effectif de l'attaque |
| Latérale ou diagonale | listes propres aux deux directions | aucune multiplication liée à la granularité numérique |

Les états actifs et passifs changent le signe de la contribution ; ils ne
changent ni la géométrie ni la liste des cellules consultées.

## 4. Résolution stochastique d'un combat

Avec `A` la puissance d'attaque et `D` la puissance de défense :

\[
P_R=\operatorname{borne}\left(
\frac13+\frac{D-A}{900},\;0{,}12,\;0{,}65
\right),\qquad
P_C=1-P_R.
\]

`PR` est la probabilité que l'attaque soit repoussée et `PC` celle d'une
capture. La référence de `1/3` n'est pas un résultat garanti partie par
partie : elle constitue le centre conditionnel lorsque `A=D`.

## 5. Contraintes numériques locales

Pour une cellule territoriale libre `c` :

\[
K(c)=\{1,2,3,4,5\}\setminus
\left(V_{\text{segment ligne}}(c)\cup
V_{\text{segment colonne}}(c)\right).
\]

Les cellules de jeu séparent les segments. Elles ne sont ni des valeurs ni des
contraintes. Une ligne ou colonne numérique complète contient chaque valeur
de 1 à 5 une seule fois et sa somme vaut `15`.

Une parcelle capturée est figée : ses nombres sortent des listes de candidats,
des mesures de blocage et de toutes les permutations numériques futures.

## 6. Cycles et permutations

Deux opérations restent indépendantes :

| Cycle | Support | Exclusions |
|---|---|---|
| Numérique | lignes/colonnes locales d'une parcelle 5×5 | parcelle capturée ; opération illégale |
| Élémentaire | ligne/colonne complète de la grille 17×17 | toute discontinuité non territoriale ; opération illégale |

Au tour `N`, le système génère un témoin sans intervention et les permutations
admissibles, puis compare leurs effets estimés au tour `N+4`. Le témoin reste
toujours un candidat. Une parcelle non capturée reconnue comme bloquée pendant
trois observations consécutives doit recevoir une correction admissible au
plus tard lors du cycle suivant.

## 7. Phases statistiques

Chaque état `s` fournit des indicateurs normalisés `fi(s)` : occupation,
remplissage des parcelles ouvertes, matériel restant, stocks de jetons,
attaques repoussées et pression terminale.

\[
G(s)=\sum_i w_i f_i(s),\qquad \sum_iw_i=1.
\]

Les seuils sont appris sur les trajectoires terminées :

\[
L_1=Q_{1/3}(G),\qquad L_2=Q_{2/3}(G).
\]

Ils séparent début, milieu et fin sans imposer de numéro de ronde fixe. Les
paramètres sont recalibrés entre les parties de test, jamais au milieu d'une
partie active, et la phase atteinte ne régresse pas.

## 8. Invariants vérifiables

- une cellule de jeu ne reçoit aucune donnée territoriale ;
- un mouvement légal ne laisse pas son propre roi en échec ;
- une parcelle capturée ne participe plus aux cycles numériques ;
- une permutation élémentaire n'utilise aucune partie d'une ligne exclue ;
- `PR + PC = 1` ;
- le témoin sans permutation est évalué à chaque décision `N+4` ;
- une seed identique reproduit les tirages d'un même scénario ;
- une simulation n'altère jamais la partie principale.
