@echo off
setlocal
set "ETAPA=%~1"
if "%ETAPA%"=="" set "ETAPA=automatico"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0atualizar_traducao.ps1" -Etapa "%ETAPA%"
exit /b %ERRORLEVEL%
