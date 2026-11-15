@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
echo Execute INSTALAR.bat primeiro.
pause
exit /b 1
)
.venv\Scripts\python.exe preparar_voz.py
if errorlevel 1 (
echo Preparacao de voz falhou. Guarde a mensagem de erro.
pause
exit /b 1
)
echo Reinicie o Aether para testar a voz.
pause
