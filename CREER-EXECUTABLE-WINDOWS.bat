@echo off
setlocal
title Creation de ElementChess.exe
cd /d "%~dp0"

echo ============================================================
echo   ELEMENTCHESS - CREATION DE L'EXECUTABLE WINDOWS
echo ============================================================
echo.
echo Ce programme va creer une version autonome de ElementChess.
echo Vous n'avez aucune commande a saisir.
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo ERREUR : Python pour Windows n'a pas ete trouve.
    echo Installez Python 3.11 ou une version plus recente,
    echo puis relancez ce fichier.
    echo.
    pause
    exit /b 1
)

if not exist ".venv-build\Scripts\python.exe" (
    echo [1/5] Creation de l'environnement de fabrication...
    py -3 -m venv .venv-build
    if errorlevel 1 goto :failure
) else (
    echo [1/5] Environnement deja disponible.
)

echo [2/5] Installation de l'outil de fabrication...
".venv-build\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :failure
".venv-build\Scripts\python.exe" -m pip install -r requirements-build.txt
if errorlevel 1 goto :failure

echo [3/5] Verification du jeu...
".venv-build\Scripts\python.exe" -m unittest discover -s tests -q
if errorlevel 1 goto :failure

echo [4/5] Creation de ElementChess.exe...
".venv-build\Scripts\pyinstaller.exe" --noconfirm --clean ElementChess.spec
if errorlevel 1 goto :failure

echo [5/5] Creation de l'archive a distribuer...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'dist\ElementChess.exe' -DestinationPath 'ElementChess-Windows-x64.zip' -Force"
if errorlevel 1 goto :failure

echo.
echo ============================================================
echo   TERMINE
echo ============================================================
echo.
echo L'executable se trouve ici :
echo   dist\ElementChess.exe
echo.
echo Le fichier a transmettre aux testeurs est :
echo   ElementChess-Windows-x64.zip
echo.
explorer.exe /select,"%CD%\ElementChess-Windows-x64.zip"
pause
exit /b 0

:failure
echo.
echo La creation a echoue. Consultez le message affiche ci-dessus.
pause
exit /b 1
