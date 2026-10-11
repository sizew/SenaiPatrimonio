@echo off
title SENAI Patrimonio - Servidor Flask :5000
color 0A
echo ========================================================
echo   INICIANDO SERVIDOR SENAI PATRIMONIO (PORTA 5000)
echo ========================================================
echo.
cd /d "%~dp0backend"
python app.py
pause
