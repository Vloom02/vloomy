@echo off
rem Compila la app, corre los tests del wake word y deja Vloomy.apk en la raiz del proyecto.
rem Todo lo que baja Gradle queda en D:\Claude\repos\vloomy\.tools (nada en C).
rem VLOOMY_RECURSOS: carpeta con .tools cuando se compila desde una copia (modo mejora).
setlocal
if defined VLOOMY_RECURSOS (set "T=%VLOOMY_RECURSOS%\.tools") else (set "T=%~dp0..\.tools")
set "JAVA_HOME=%T%\jdk-21"
set "ANDROID_HOME=%T%\android-sdk"
set "ANDROID_USER_HOME=%T%\android-home"
set "GRADLE_USER_HOME=%T%\gradle-home"
pushd "%~dp0"
call "%~dp0gradlew.bat" --no-daemon :wake:test :app:assembleDebug
if errorlevel 1 (popd & exit /b 1)
copy /y "%~dp0app\build\outputs\apk\debug\app-debug.apk" "%~dp0..\Vloomy.apk" >nul
popd
echo Listo: Vloomy.apk