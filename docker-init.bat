@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo   Vox Local Story TTS - Docker Setup
echo ========================================
echo.

docker version >nul 2>&1
if errorlevel 1 (
  echo ERROR: Docker Desktop is not installed or not running.
  echo Install/start Docker Desktop, then run this file again.
  pause
  exit /b 1
)

docker compose version >nul 2>&1
if errorlevel 1 (
  echo ERROR: Docker Compose is not available.
  pause
  exit /b 1
)

if not exist ".env" (
  copy /Y ".env.example" ".env" >nul
  powershell -NoProfile -Command "(Get-Content .env) -replace '^HOST=.*','HOST=0.0.0.0' -replace '^PORT=.*','PORT=8010' | Set-Content .env"
  echo Created .env
)

if not exist "audio_cache" mkdir audio_cache
if not exist "logs" mkdir logs

echo.
echo Building Docker image...
docker compose build
if errorlevel 1 goto :fail

echo.
echo Starting service...
docker compose up -d
if errorlevel 1 goto :fail

echo.
echo Waiting for service...
for /L %%i in (1,1,30) do (
  powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:8010/health | Out-Null; exit 0 } catch { exit 1 }"
  if not errorlevel 1 goto :ok
  timeout /t 2 /nobreak >nul
)

echo Service did not become healthy. Recent logs:
docker compose logs --tail=100 vox-tts
goto :fail

:ok
echo.
echo ========================================
echo   READY: http://localhost:8010
echo ========================================
start "" http://localhost:8010
pause
exit /b 0

:fail
echo.
echo Deployment failed. Run: docker compose logs -f vox-tts
pause
exit /b 1
