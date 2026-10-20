@echo off
rem Muestra en vivo el volumen del microfono y el puntaje de "Hey Vloomy" / "Hey Jarvis".
cd /d "%~dp0voice"
".venv\Scripts\python.exe" diagnostico.py %*
pause