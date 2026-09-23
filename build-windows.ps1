$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

if (-not (Test-Path ".venv-build")) {
    py -3.11 -m venv .venv-build
}

& ".\.venv-build\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv-build\Scripts\python.exe" -m pip install -r requirements-build.txt
& ".\.venv-build\Scripts\python.exe" -m unittest discover -s tests -v
& ".\.venv-build\Scripts\pyinstaller.exe" --noconfirm --clean ElementChess.spec

Write-Host ""
Write-Host "Exécutable créé : dist\ElementChess.exe"

