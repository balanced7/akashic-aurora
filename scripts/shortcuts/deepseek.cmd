@echo off
rem Double-click (or run `deepseek` from the repo) to open an interactive DeepSeek chat window.
rem Passes any args through, e.g.  deepseek --no-think  /  deepseek --load mychat.json
cd /d "%~dp0"
py scripts\deepseek_chat.py %*
if errorlevel 1 pause
