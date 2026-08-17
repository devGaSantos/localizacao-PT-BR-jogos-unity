@echo off
setlocal
set "ETAPA=%~1"
if "%ETAPA%"=="" set "ETAPA=atualizar"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0atualizar_traducao.ps1" -Etapa "%ETAPA%"
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if not "%EXIT_CODE%"=="0" echo O pipeline terminou com erro. Confira a mensagem acima.
pause
exit /b %EXIT_CODE%
