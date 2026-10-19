@echo off
rem Capa 2 de Vloomy: sesion de Claude Code (con tu suscripcion) que recibe las tareas pesadas.
rem La primera vez: inicia sesion con tu cuenta de Claude y acepta los avisos del canal de desarrollo.
cd /d "%~dp0capa2"
"%~dp0node_modules\.bin\claude.cmd" --dangerously-load-development-channels server:vloomy
pause