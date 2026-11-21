@echo off
chcp 65001 >nul
title MIZU KIZUNA
cd /d "%~dp0"
rem Arrete un ancien serveur MIZU KIZUNA encore ouvert sur le port 8000
for /f "tokens=5" %%p in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /PID %%p /F >nul 2>nul
where python >nul 2>nul || (echo Python introuvable. Installez Python 3.10+ depuis python.org & pause & exit /b)
if not exist .venv (
  echo Installation (premiere fois, quelques minutes^)...
  python -m venv .venv
  call .venv\Scripts\activate
  python -m pip install --upgrade pip
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate
)
echo.
echo  MIZU KIZUNA v2.4 demarre sur http://localhost:8000  (fermez cette fenetre pour arreter)
echo.
start "" cmd /c "timeout /t 4 >nul & start http://localhost:8000"
python -m uvicorn main:app --host 0.0.0.0 --port 8000
pause
