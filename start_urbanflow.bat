@echo off
echo ========================================================
echo Starting UrbanFlow AI - Autonomous Traffic Command Center
echo ========================================================
echo.

echo [1/2] Starting Backend Server (http://localhost:8000)...
start "UrbanFlow Backend (FastAPI)" cmd /k "cd /d %~dp0backend && (py -3 run.py 2>nul || python run.py)"

timeout /t 2 /nobreak >nul

echo [2/2] Starting Frontend Dashboard (http://localhost:5173)...
start "UrbanFlow Frontend (Vite/React)" cmd /k "cd /d %~dp0frontend && call npm.cmd run dev"

echo.
echo ========================================================
echo Both servers are launching!
echo Frontend Dashboard: http://localhost:5173
echo Backend API Docs:   http://localhost:8000/docs
echo ========================================================
