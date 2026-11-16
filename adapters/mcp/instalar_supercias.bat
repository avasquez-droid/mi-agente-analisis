@echo off
chcp 65001 >nul
cd /d "%~dp0..\.."
where python >nul 2>nul
if %errorlevel%==0 (
  python adapters\mcp\instalar_claude_desktop.py
) else (
  py -3 adapters\mcp\instalar_claude_desktop.py
)
if errorlevel 9009 (
  echo No se encontro Python. Instalelo desde python.org y vuelva a intentar.
  pause
)
