@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "MINDLINE_MODE=%~1"
if not defined MINDLINE_MODE set "MINDLINE_MODE=mock"

if /I not "%MINDLINE_MODE%"=="mock" if /I not "%MINDLINE_MODE%"=="qwen" (
  echo Usage: run.cmd [mock^|qwen]
  exit /b 2
)

echo Starting MindLine in %MINDLINE_MODE% mode...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_mindline.ps1" -LlmMode "%MINDLINE_MODE%"
set "MINDLINE_EXIT=%ERRORLEVEL%"

if not "%MINDLINE_EXIT%"=="0" (
  echo.
  echo MindLine failed to start. Review the error above.
  pause
)

exit /b %MINDLINE_EXIT%
