#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "============================================================"
echo "  ELEMENTCHESS - CRÉATION DE LA DISTRIBUTION LINUX"
echo "============================================================"

python3 -m venv .venv-build
.venv-build/bin/python -m pip install --upgrade pip
.venv-build/bin/python -m pip install -r requirements-build.txt
.venv-build/bin/python -c "import tkinter; print('Tkinter : OK')"
.venv-build/bin/python -m unittest discover -s tests -q
.venv-build/bin/python -m PyInstaller --noconfirm --clean --log-level WARN ElementChess.spec

cp README-LINUX.txt dist/ElementChess/README.txt
tar -C dist -czf ElementChess-Linux-x64.tar.gz ElementChess

echo
echo "Distribution créée : ElementChess-Linux-x64.tar.gz"
echo "Exécutable : dist/ElementChess/ElementChess"
