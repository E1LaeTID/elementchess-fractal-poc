ELEMENTCHESS — PROOF OF CONCEPT WINDOWS
=======================================

Merci de tester ElementChess.

Cette version est une preuve de concept qui transforme le jeu d'échecs
classique en jeu de stratégie stochastique sur une grille mixte de 17 x 17
cellules.


INSTALLATION
------------

1. Faites un clic droit sur ElementChess-Windows-x64.zip.
2. Choisissez « Extraire tout ».
3. Ouvrez le dossier ElementChess extrait.
4. Double-cliquez sur ElementChess.exe.

Le jeu ne nécessite ni Python, ni Visual Studio Code, ni invite de commandes.

IMPORTANT : ne déplacez pas ElementChess.exe en dehors de son dossier.
Le dossier _internal placé à côté de l'exécutable contient les bibliothèques
nécessaires au fonctionnement du jeu.


AVERTISSEMENT WINDOWS
---------------------

Cette version expérimentale n'est pas encore signée avec un certificat de
signature de code. Windows peut donc afficher un avertissement SmartScreen.

N'exécutez le programme que s'il provient du dépôt officiel :
https://github.com/E1LaeTID/elementchess-fractal-poc

Si Windows affiche « Windows a protégé votre ordinateur », cliquez sur
« Informations complémentaires », puis sur « Exécuter quand même ».


COMMANDES PRINCIPALES
---------------------

1 ou T       Vue territoriale
2 ou E       Vue mixte des pièces et du terrain
Maj          Affichage temporaire des nombres
Ctrl         Potentiels d'attaque et de défense au survol
Alt          Sélection défensive du roi et de la tour
4 ou H       Roues élémentaires et interstice
F1 ou G      Notice de jeu
F2 ou L      Scénarios de simulation
F11          Plein écran


OBJECTIFS DU TEST
-----------------

Vos retours sont particulièrement utiles sur :

- la compréhension du déroulement d'un tour ;
- le placement des jetons numérotés ;
- les déplacements et orientations des pièces ;
- la lisibilité des états élémentaires ;
- la fréquence des attaques repoussées ;
- les cycles de permutation ;
- l'équilibre entre échec et mat, capture territoriale, accumulation de
  jetons et risque de trois attaques repoussées ;
- les blocages, erreurs ou fins de partie non détectées.


SIGNALER UN PROBLÈME
--------------------

Vous pouvez signaler un problème ici :
https://github.com/E1LaeTID/elementchess-fractal-poc/issues

Merci d'indiquer si possible :

- votre version de Windows ;
- l'étape du tour concernée ;
- le résultat attendu ;
- le résultat observé ;
- une capture d'écran.


LICENCE
-------

Cette version est fournie pour évaluation personnelle, pédagogique et non
commerciale conformément à l'ElementChess Public Evaluation License 1.0.

Copyright (c) 2026 Pascal Quesdyel. Tous droits réservés.
