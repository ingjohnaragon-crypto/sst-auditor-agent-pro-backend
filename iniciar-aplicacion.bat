@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
chcp 65001 >nul

rem Levanta PostgreSQL, migraciones, semillas, el API y Angular sin ventanas extra.
rem Detener: iniciar-aplicacion.bat detener

if /I "%~1"=="detener" goto detener

set "FRONTEND=%~dp0..\sst-auditor-agent-pro-frontend"
for %%I in ("%FRONTEND%") do set "FRONTEND=%%~fI"
set "PYTHON=%CD%\.venv\Scripts\python.exe"
if not exist logs mkdir logs

where docker >nul 2>&1
if errorlevel 1 (
  echo No se encontro Docker. Abre Docker Desktop y vuelve a ejecutar este archivo.
  goto pausa_error
)
if not exist "%PYTHON%" (
  echo No esta el entorno de Python. En esta carpeta ejecuta: poetry install
  goto pausa_error
)
if not exist "%CD%\.env" (
  echo Falta .env. Copia .env.example a .env y vuelve a ejecutar este archivo.
  goto pausa_error
)
if not exist "%FRONTEND%\package.json" (
  echo No esta el frontend en %FRONTEND%
  goto pausa_error
)
where npm >nul 2>&1
if errorlevel 1 (
  echo No se encontro npm. Instala Node.js y vuelve a ejecutar este archivo.
  goto pausa_error
)

echo Levantando PostgreSQL...
docker compose version >nul 2>&1
if errorlevel 1 (
  docker-compose up -d
) else (
  docker compose up -d
)
if errorlevel 1 goto pausa_error

echo Esperando a que PostgreSQL quede listo...
set INTENTOS=0
:esperar_postgres
set /a INTENTOS+=1
if !INTENTOS! GTR 30 (
  echo PostgreSQL no quedo listo. Revisa: docker compose ps
  goto pausa_error
)
set ESTADO=
for /f "delims=" %%s in ('docker inspect --format "{{.State.Health.Status}}" sst_auditor_postgres 2^>nul') do set ESTADO=%%s
if /I "!ESTADO!"=="healthy" goto migrar
ping -n 3 127.0.0.1 >nul
goto esperar_postgres

:migrar
echo Aplicando migraciones...
"%PYTHON%" -m alembic upgrade head
if errorlevel 1 goto pausa_error

echo Sembrando catalogos...
"%PYTHON%" -m scripts.sembrar_datos
if errorlevel 1 goto pausa_error

call :puerto_en_uso 8000
if "!PUERTO_EN_USO!"=="1" (
  echo El API ya escucha en el puerto 8000.
) else (
  echo Iniciando el API...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$p = Start-Process -FilePath '%PYTHON%' -ArgumentList '-m','uvicorn','src.main:app','--reload','--host','127.0.0.1','--port','8000' -WorkingDirectory '%CD%' -WindowStyle Hidden -RedirectStandardOutput '%CD%\logs\api.log' -RedirectStandardError '%CD%\logs\api.err.log' -PassThru; Set-Content -Path '%CD%\logs\api.pid' -Value $p.Id"
  if errorlevel 1 goto pausa_error
)

if not exist "%FRONTEND%\node_modules\" (
  echo Instalando dependencias de Angular...
  pushd "%FRONTEND%"
  call npm install
  if errorlevel 1 (
    popd
    goto pausa_error
  )
  popd
)

call :puerto_en_uso 4200
if "!PUERTO_EN_USO!"=="1" (
  echo Angular ya escucha en el puerto 4200.
) else (
  echo Iniciando Angular...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$p = Start-Process -FilePath 'cmd.exe' -ArgumentList '/c','npm start -- --host 127.0.0.1 --port 4200' -WorkingDirectory '%FRONTEND%' -WindowStyle Hidden -RedirectStandardOutput '%CD%\logs\angular.log' -RedirectStandardError '%CD%\logs\angular.err.log' -PassThru; Set-Content -Path '%CD%\logs\angular.pid' -Value $p.Id"
  if errorlevel 1 goto pausa_error
)

echo.
echo La aplicacion quedo en marcha. Puedes cerrar esta ventana.
echo API:      http://127.0.0.1:8000/docs
echo Frontend: http://localhost:4200
echo Logs:     logs\api.log y logs\angular.log
echo Detener:  iniciar-aplicacion.bat detener
echo.
pause
exit /b 0

:detener
echo Deteniendo API y Angular...
call :matar_pid logs\api.pid
call :matar_pid logs\angular.pid
call :matar_puerto 8000
call :matar_puerto 4200
echo Deteniendo PostgreSQL...
docker compose version >nul 2>&1
if errorlevel 1 (
  docker-compose stop
) else (
  docker compose stop
)
echo Aplicacion detenida. Los datos de PostgreSQL se conservan.
pause
exit /b 0

:puerto_en_uso
set PUERTO_EN_USO=0
powershell -NoProfile -Command "$c = New-Object System.Net.Sockets.TcpClient; try { $c.Connect('127.0.0.1', %~1); $c.Close(); exit 0 } catch { exit 1 }"
if not errorlevel 1 set PUERTO_EN_USO=1
exit /b 0

:matar_pid
if not exist "%~1" exit /b 0
for /f "usebackq delims=" %%p in ("%~1") do taskkill /PID %%p /T /F >nul 2>&1
del /q "%~1" >nul 2>&1
exit /b 0

:matar_puerto
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-NetTCPConnection -LocalPort %~1 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $PSItem.OwningProcess -Force -ErrorAction SilentlyContinue }"
exit /b 0

:pausa_error
echo.
echo No se pudo iniciar la aplicacion.
pause
exit /b 1
