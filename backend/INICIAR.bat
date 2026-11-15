@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
echo Execute INSTALAR.bat primeiro.
pause
exit /b 1
)
echo Abra http://127.0.0.1:8000/painel no navegador.
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
pause
