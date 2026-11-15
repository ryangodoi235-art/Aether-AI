@echo off
cd /d "%~dp0"
call INSTALAR.bat
if errorlevel 1 exit /b 1
ollama pull qwen2.5:3b
if errorlevel 1 goto erro
.venv\Scripts\python.exe preparar_voz.py
if errorlevel 1 goto erro
echo Preparacao concluida. Execute INICIAR_COMPLETO.bat.
pause
exit /b 0
:erro
echo Preparacao incompleta. Copie o erro exibido.
pause
exit /b 1
