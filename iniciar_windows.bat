@echo off
rem MicroGrano Lab para Windows: prepara el entorno de Python si hace falta y abre la interfaz.
rem Alternativa a "MicroGrano Lab.exe": hace lo mismo y muestra el progreso en esta ventana.
rem Opciones: --reparar (recrea el entorno), --solo-instalar, --comprobar.
setlocal EnableExtensions
cd /d "%~dp0"
set "ARRANQUE=%~dp0lanzador\arranque.py"
set "MICROGRANO_SIN_PAUSA=1"
if not exist "%ARRANQUE%" (
  echo No se encontro lanzador\arranque.py. Ejecute este archivo dentro de la carpeta del repositorio.
  pause
  exit /b 1
)

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "import sys,sysconfig; sys.exit(0 if sys.version_info[:2] == (3, 13) and sys.maxsize > 2**32 and not sysconfig.get_config_var('Py_GIL_DISABLED') and getattr(sys, '_is_gil_enabled', lambda: True)() else 1)" >nul 2>&1
  if not errorlevel 1 (
    ".venv\Scripts\python.exe" "%ARRANQUE%" --consola %*
    goto :fin
  )
)

call :buscar_python
if defined PYCMD (
  %PYCMD% "%ARRANQUE%" --consola %*
  goto :fin
)

echo.
echo MicroGrano Lab necesita Python 3.13 de 64 bits con GIL y no se encontro en este equipo.
where winget >nul 2>&1
if errorlevel 1 goto :descargar
choice /C SN /M "Desea instalar Python 3.13 ahora con winget, solo para su usuario"
if errorlevel 2 goto :descargar
winget install -e --id Python.Python.3.13 --scope user --accept-package-agreements --accept-source-agreements
call :buscar_python
if defined PYCMD (
  %PYCMD% "%ARRANQUE%" --consola %*
  goto :fin
)
echo Python se instalo. Cierre esta ventana y vuelva a abrir el lanzador.
pause
exit /b 1

:descargar
echo Descargue Python 3.13 desde https://www.python.org/downloads/ y marque "Add python.exe to PATH".
start "" "https://www.python.org/downloads/"
pause
exit /b 1

:fin
set "CODIGO=%errorlevel%"
if not "%CODIGO%"=="0" (
  echo.
  pause
)
exit /b %CODIGO%

rem Busca el lanzador oficial "py" y, en su defecto, python.exe (sin el alias de Microsoft Store).
:buscar_python
set "PYCMD="
for %%D in ("%LOCALAPPDATA%\Programs\Python\Launcher" "%WINDIR%") do (
  if not defined PYCMD if exist "%%~D\py.exe" (
    "%%~D\py.exe" -3.13 -c "import sys,sysconfig; sys.exit(0 if sys.version_info[:2] == (3, 13) and sys.maxsize > 2**32 and not sysconfig.get_config_var('Py_GIL_DISABLED') and getattr(sys, '_is_gil_enabled', lambda: True)() else 1)" >nul 2>&1
    if not errorlevel 1 set PYCMD="%%~D\py.exe" -3.13
  )
)
if defined PYCMD exit /b 0
for /f "delims=" %%P in ('where python 2^>nul') do (
  if not defined PYCMD (
    echo %%P| find /i "WindowsApps" >nul
    if errorlevel 1 (
      "%%P" -c "import sys,sysconfig; sys.exit(0 if sys.version_info[:2] == (3, 13) and sys.maxsize > 2**32 and not sysconfig.get_config_var('Py_GIL_DISABLED') and getattr(sys, '_is_gil_enabled', lambda: True)() else 1)" >nul 2>&1
      if not errorlevel 1 set PYCMD="%%P"
    )
  )
)
exit /b 0
