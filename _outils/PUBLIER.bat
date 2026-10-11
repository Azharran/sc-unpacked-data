@echo off
chcp 65001 >nul
title LYRA - Publication des donnees du jeu
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
python publier.py %*
echo.
pause
