from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GuidePage:
    chapter: str
    title: str
    body: str

    @property
    def menu_label(self) -> str:
        return f"{self.chapter}. {self.title}"


GUIDE_PAGES: tuple[GuidePage, ...] = (
    GuidePage(
        "I",
        "Déroulement de la partie",
        """AVANT LE PREMIER TOUR

Tant que le numéro du tour n'est pas affiché, les joueurs attendent. Durant cette période, les éléments sont attribués aux cellules terrain selon le modèle d'assignation de la partie.

Chaque joueur reçoit cinq numéros au lancement, puis deux à chaque interstice. Il peut les placer uniquement dans une parcelle 5×5 où se trouve au moins une de ses pièces, ou les conserver pour un tour ultérieur, dans la limite d'une réserve de 21 jetons.

DÉBUT DU TOUR

Lorsque le numéro du tour s'affiche, le joueur Blanc commence. Il peut d'abord placer un ou plusieurs numéros, ou passer cette phase sans en poser. Il choisit ensuite une pièce, la déplace, puis fixe son orientation.

Le joueur Noir effectue ensuite les mêmes actions. Le passage de Blanc à Noir est immédiat, comme dans une partie d'échecs classique.

ENTRE-DEUX TOURS

Trois éléments distincts sont tirés au sort. Une orientation confirmée qui pointe l'un de ces éléments peut compléter automatiquement la ligne et la colonne locales de la cellule visée, au bénéfice du camp majoritaire dans cette parcelle.""",
    ),
    GuidePage(
        "II",
        "Le terrain",
        """La tracé des lignes du jeu d'échecs classique est remplacé par un environnement élémentaire.

Chaque pièce dispose d'un environnement de huit cellules terrain qu'aucune autre pièce de l'échiquier ne peut occuper.

Le terrain central est structuré en neuf zones de 5×5 formant une grille de morpion. Une circonférence élémentaire sans numéro entoure ce carré 15×15.

Chaque cellule terrain possède un état élémentaire vers lequel une pièce peut pointer.

LECTURE DES POTENTIELS

Sélectionnez d'abord une pièce dans le board mixte. Ses destinations légales apparaissent en bleu et ses parcours en émeraude. Maintenez ensuite CTRL et survolez une destination bleue : une infobulle indique les fourchettes potentielles d'attaque et de défense. Ces valeurs illustrent l'influence du terrain sans résoudre le combat à votre place.

NUMÉROTATION

Une cellule terrain peut recevoir un numéro de 1 à 5. Dans une même zone 5×5, les valeurs identiques ne peuvent pas se répéter dans le même segment continu de ligne ou de colonne. Une case réservée aux pièces coupe la ligne ou la colonne : les nombres situés de part et d'autre appartiennent à des segments indépendants.

Le joueur qui possède le plus de numéros lorsque la zone 5×5 est correctement complétée capture ce terrain. La parcelle devient lumineuse à sa couleur, se verrouille et ses numéros ne participent plus aux rotations. Ce halo colore uniquement le support : les pièces restent dessinées intégralement au premier plan.

Si vos placements bloquent une parcelle avant sa capture, vous pouvez recycler tous les jetons que vous y avez posés. Le recyclage est toujours total : vous ne pouvez pas en retirer seulement une partie. Une réserve déjà proche de 21 peut faire perdre les jetons qui ne peuvent plus y rentrer.""",
    ),
    GuidePage(
        "III",
        "Orientation des pièces",
        """Une pièce possède huit orientations possibles : nord, nord-est, est, sud-est, sud, sud-ouest, ouest et nord-ouest.

L'orientation est fixée après le placement ou le déplacement de la pièce. La flèche visible dans la cellule indique l'orientation active.

VERROUILLER ouvre la confirmation. RETOUR annule alors tout le déplacement et replace la pièce sur sa case de départ ; si une capture avait eu lieu, la pièce adverse est également restaurée.

DÉPLACEMENT DÉFENSIF ROI-TOUR

Maintenez ALT et sélectionnez votre roi et une tour, dans n'importe quel ordre. Les deux pièces doivent être sur la même ligne et aucune pièce ne doit les séparer. La tour doit être sur un bord latéral : elle avance de deux cases dans le sens opposé au bord, puis le roi se place contre elle du côté de ce bord. La position finale doit sortir le roi de l'échec. Vous orientez ensuite la tour, puis le roi, et le tour ne se termine qu'après les deux confirmations.

Un pion qui atteint l'extrémité opposée est immédiatement remplacé par une dame avant le choix de son orientation.

Lorsqu'un roi est attaqué, sa case est encadrée en rouge et le message ÉCHEC BLANC ou ÉCHEC NOIR reste visible pendant le choix d'orientation. Tous les coups sont simulés avant affichage : seules une sortie du roi vers une case sûre, une capture de l'attaquant ou une interposition supprimant effectivement l'échec sont autorisées.

Durant l'interstice, une orientation déjà confirmée déclenche un bonus si elle pointe une cellule portant l'un des éléments tirés. Les cases encore vides de la ligne et de la colonne locales qui contiennent cette cellule sont complétées automatiquement.

Le bonus appartient au camp qui occupe majoritairement la parcelle visée, même si ce n'est pas le camp de la pièce orientée. En cas d'occupation commune, le jeu compare d'abord le nombre de pièces, puis le nombre de jetons déjà posés par chaque camp. Une égalité parfaite ne produit aucun bonus arbitraire.""",
    ),
    GuidePage(
        "IV",
        "Les roues élémentaires",
        """VOS CHOIX FONT TOURNER LES ROUES

Chaque jeton que vous placez donne de la valeur à une cellule terrain. Son élément et sa position sur le plateau participent au score qui fera tourner les roues.

Lorsque vous déplacez une pièce, son orientation compte également : la direction que vous lui donnez désigne la partie de son environnement élémentaire vers laquelle elle agit. Le placement de vos jetons et l'orientation de vos pièces construisent donc ensemble votre influence sur les roues.

À LA FIN DE LA RONDE

Lorsque Blanc et Noir ont tous les deux terminé leur déplacement et verrouillé leur orientation, les roues élémentaires tournent selon les scores obtenus sur le terrain. Aucun calcul de roue n'interrompt le passage de Blanc à Noir. La position des cellules sur leur ligne est évaluée relativement à la destination de chaque camp : progresser vers la ligne de promotion des pions renforce le sens positif, rester sur les lignes arrière agit dans le sens négatif, et la ligne centrale reste neutre.

Après chaque déplacement, la roue principale marque aussi le temps d'un cran et entraîne mécaniquement les quatre roues qui la touchent, puis le reste du train denté. Cette impulsion régulière est indépendante du calcul des scores, qui n'a lieu qu'à l'interstice.

Cette rotation crée un court interstice entre la fin de la ronde et l'annonce de la suivante. Vous pouvez alors observer les conséquences des choix des deux joueurs : les roues avancent ou reculent et le terrain se transforme.

Vous n'avez aucun calcul à effectuer : le jeu annonce les rotations et rend leurs effets visibles avant de vous rendre la main.""",
    ),
    GuidePage(
        "V",
        "Conditions de victoire",
        """Un joueur remporte la partie s'il réalise l'une des conditions suivantes :

• mettre le roi adverse échec et mat ;
• capturer un alignement de trois terrains : ligne, colonne ou diagonale.

Trois parcelles capturées et alignées déclenchent immédiatement la victoire. La fenêtre finale nomme le gagnant et le perdant, puis propose de recommencer une nouvelle partie ou de quitter le jeu.""",
    ),
    GuidePage(
        "VI",
        "Conditions de défaite",
        """Conditions relevées dans la notice de travail :

• la réserve est plafonnée à 21 jetons : aucun jeton supplémentaire n'est ajouté tant qu'une place ne s'est pas libérée ;
• remplir sa jauge de trois attaques repoussées. Un cran disparaît après deux coups consécutifs du joueur sans nouvelle attaque ratée.

La jauge et la récupération sont actives dans le moteur du prototype.""",
    ),
    GuidePage(
        "VII",
        "Commandes du jeu",
        """COMMANDES ACTUELLES DU PROTOTYPE

1 ou T    Vue terrain
2 ou E    Board mixte
3 ou N    Vue numérotation
4 ou H    Vue du temps incrémental et commandes des roues
PASSER    Conserver les jetons non joués et poursuivre le tour
RECYCLER  Reprendre en totalité vos jetons d'une parcelle non capturée
R         Régénérer les numéros de démonstration
Flèches   Déplacer la sélection
ZQSD      Déplacer la sélection
F11       Plein écran
F1 ou G   Ouvrir ou fermer cette notice
F2 ou L   Ouvrir le livret de simulations
2         En simulation : reprendre la partie ou en commencer une nouvelle
Échap     Fermer la notice, puis quitter le jeu

Dans la notice : sélectionner un chapitre dans le sommaire ou utiliser Page précédente / Page suivante.""",
    ),
    GuidePage(
        "VIII",
        "Glossaire",
        """CELLULE TERRAIN
Unité environnementale portant un élément et, dans le carré central, éventuellement un numéro.

CELLULE D'ÉCHIQUIER
Position impair/impair pouvant accueillir une pièce. Elle se superpose au terrain sans supprimer son état.

TERRAIN 5×5
Zone de 25 cellules participant à la conquête de type morpion.

INTERSTICE
Phase de transformation ouverte après les coups de Blanc et de Noir, entre la fin d'une ronde et le début de la suivante.

ROUE PRINCIPALE
Mécanisme temporel avançant d'une dent par tour et entraînant plusieurs roues élémentaires.

ROUE ÉLÉMENTAIRE
Mécanisme recevant un score déterminé par les actions et états du board.""",
    ),
)


class GuideBook:
    def __init__(self, pages: tuple[GuidePage, ...] = GUIDE_PAGES) -> None:
        if not pages:
            raise ValueError("La notice doit contenir au moins une page")
        self.pages = pages
        self.index = 0

    @property
    def current(self) -> GuidePage:
        return self.pages[self.index]

    def select(self, index: int) -> GuidePage:
        self.index = max(0, min(len(self.pages) - 1, index))
        return self.current

    def next(self) -> GuidePage:
        return self.select(self.index + 1)

    def previous(self) -> GuidePage:
        return self.select(self.index - 1)
