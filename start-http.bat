@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=python"
if exist ".venv-gpu\Scripts\python.exe" set "PYTHON_EXE=.venv-gpu\Scripts\python.exe"

if "%SKY_MCP_TOKEN%"=="" (
  for /f "delims=" %%t in ('"%PYTHON_EXE%" sky-mcp-server.py --print-token') do set "SKY_MCP_TOKEN=%%t"
)

echo.
echo Sky MCP Server
echo ------------------------------
echo URL:   http://0.0.0.0:9800
echo Token: %SKY_MCP_TOKEN%
echo.
echo Keep this window open while playing.
echo For Polaris, use your computer LAN IP and this token.
echo.

"%PYTHON_EXE%" sky-mcp-server.py --http --host 0.0.0.0 --port 9800 --token "%SKY_MCP_TOKEN%"
pause
