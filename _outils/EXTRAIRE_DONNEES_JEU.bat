@echo off
chcp 65001 >nul
title LYRA - Extraction des donnees du jeu
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
echo.
echo  Extraction des donnees de Star Citizen (environ 30 minutes).
echo  Docker Desktop doit etre lance. Le jeu peut rester ferme.
echo.
python extraire.py %*
echo.
pause
