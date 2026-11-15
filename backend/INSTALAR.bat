@echo off
cd /d "%~dp0"
python --version
if errorlevel 1 goto erro
if not exist ".venv\Scripts\python.exe" python -m venv .venv
if errorlevel 1 goto erro
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto erro
.venv\Scripts\python.exe -m pip install -r requirements-features.txt -r requirements-forecast.txt
if errorlevel 1 goto erro
.venv\Scripts\python.exe -m pip check
if errorlevel 1 goto erro
echo Instalacao concluida. Execute INICIAR.bat.
pause
exit /b 0
:erro
echo Falha na instalacao. Copie a mensagem e envie no chat.
pause
exit /b 1
