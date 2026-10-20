@echo off
rem Graba tu voz para ajustar "Hey Vloomy" (unos 2 minutos).
cd /d "%~dp0voice"
".venv\Scripts\python.exe" grabar_voz.py
pause