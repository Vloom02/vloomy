@echo off
rem Arranca Vloomy en la PC (micro, parlantes y servidor para el celular).
cd /d "%~dp0voice"
".venv\Scripts\python.exe" vloomy.py %*
pause