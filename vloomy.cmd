@echo off
rem Arranca Vloomy (fase 1). Todo vive en D:\Claude\repos\vloomy.
cd /d "%~dp0voice"
".venv\Scripts\python.exe" vloomy.py
pause
