#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

echo "============================================================"
echo "  ELEMENTCHESS - CRÉATION DE L'APPLICATION macOS"
echo "============================================================"

python3 -m venv .venv-build
.venv-build/bin/python -m pip install --upgrade pip
.venv-build/bin/python -m pip install -r requirements-build.txt
.venv-build/bin/python -m unittest discover -s tests -q
.venv-build/bin/python -m PyInstaller --noconfirm --clean --log-level WARN ElementChess.spec

rm -rf package/ElementChess-macOS
mkdir -p package/ElementChess-macOS
cp -R dist/ElementChess.app package/ElementChess-macOS/
cp README-MACOS.txt package/ElementChess-macOS/README.txt
ditto -c -k --sequesterRsrc --keepParent package/ElementChess-macOS ElementChess-macOS.zip

echo
echo "Distribution créée : ElementChess-macOS.zip"
echo "Application : dist/ElementChess.app"

