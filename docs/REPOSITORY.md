# Publication du dépôt GitHub

## Identité recommandée

- **Nom du dépôt :** `elementchess-fractal-poc`
- **Visibilité :** publique
- **Description GitHub :** `Proof of concept Python transformant les échecs en jeu de stratégie stochastique sur grille mixte 17×17, à l'aide du modèle fractal universel étendu et de la Balance Map.`
- **Topics :** `chess`, `python`, `tkinter`, `game-balance`, `stochastic-game`, `procedural-systems`, `fractal-model`, `proof-of-concept`

Le nom distingue le prototype scientifique et jouable du futur produit
commercial `ElementChess` destiné à Steam.

## Options de création sur GitHub

Le dossier contient déjà son README, son `.gitignore` et sa licence. Dans le
formulaire de création GitHub :

- laisser **Add README** désactivé ;
- laisser **Add .gitignore** sur `No .gitignore` ;
- laisser **Add license** sur `None` ;
- créer le dépôt, puis envoyer l'arborescence ci-dessous.

La licence personnalisée sera détectée comme licence non standard. Elle permet
l'évaluation non commerciale tout en réservant l'exploitation commerciale et
la future publication Steam.

## Arborescence à publier

```text
elementchess-fractal-poc/
├── .github/
│   └── workflows/
│       └── windows-executable.yml
├── config/
│   ├── balance-map.template.json
│   └── balance.default.json
├── docs/
│   ├── BALANCE_MAP_DICTIONARY.md
│   ├── ELEMENTCHESS.md
│   └── REPOSITORY.md
├── elementchess/
│   ├── __init__.py
│   ├── __main__.py
│   └── … modules du moteur et de l'interface …
├── tests/
│   └── … tests automatisés …
├── .gitignore
├── BALANCE.md
├── ElementChess.spec
├── LICENSE
├── README.md
├── balance-report-sample.json
├── build-windows.ps1
├── main.py
├── pyproject.toml
└── requirements-build.txt
```

Ne pas publier `tmp/`, `build/`, `dist/`, les caches Python, les anciennes
éditions PDF incrémentales ou un exécutable produit localement.

## Obtenir l'exécutable Windows

À chaque envoi sur `main`, GitHub Actions :

1. installe Python et PyInstaller ;
2. exécute les tests ;
3. fabrique `ElementChess.exe` sans fenêtre console ;
4. fournit `ElementChess-Windows-x64.zip` dans les artefacts du workflow.

Pour fournir un téléchargement public stable, créer un tag, par exemple :

```bash
git tag v0.26.2
git push origin v0.26.2
```

Le workflow crée alors une GitHub Release et y joint automatiquement
`ElementChess-Windows-x64.zip`. Le testeur télécharge l'archive, l'extrait et
double-clique sur `ElementChess.exe` : Python, VS Code et un terminal ne sont
pas nécessaires.

Pour fabriquer le même exécutable localement sous Windows, faire un clic droit
sur `build-windows.ps1`, choisir **Exécuter avec PowerShell**, puis récupérer
`dist/ElementChess.exe`.

