@echo off
rem Startet SEO-Werkbank lokal: http://localhost:8000 (nur dieser PC)
cd /d "%~dp0backend"
start "" http://localhost:8000
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
