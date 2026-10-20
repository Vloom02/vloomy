@echo off
rem Capa 2 de Vloomy: Claude Code con tu suscripcion.
rem Solo hace falta abrirlo UNA vez: iniciar sesion y aceptar confiar en la carpeta. Despues Vloomy lo usa solo, sin ventana.
cd /d "%~dp0capa2"
"%~dp0node_modules\@anthropic-ai\claude-code\bin\claude.exe"
pause