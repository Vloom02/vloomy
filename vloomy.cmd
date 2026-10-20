@echo off
rem Arranca Vloomy en la PC (micro, parlantes, panel y servidor para el celular).
cd /d "%~dp0voice"
:arrancar
".venv\Scripts\python.exe" vloomy.py %*
rem Codigo 3: Vloomy aplico o deshizo una mejora y pidio reiniciarse (sin abrir otro panel).
if %errorlevel%==3 (set "VLOOMY_REINICIO=1" & goto arrancar)
pause