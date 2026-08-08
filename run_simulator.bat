@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%CD%\src"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -m arista_sim
  goto done
)
where python >nul 2>nul
if not errorlevel 1 (
  python -m arista_sim
  goto done
)
set "CODEX_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%CODEX_PY%" (
  "%CODEX_PY%" -m arista_sim
  goto done
)
echo Python 3.11 or newer was not found.
echo Install Python from https://www.python.org/downloads/ and try again.
:done
if errorlevel 1 pause
