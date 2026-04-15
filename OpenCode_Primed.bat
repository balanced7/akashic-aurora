@echo off
REM OpenCode Primed Launcher with Crash-Safe Logging
REM =================================================
REM - Opens a NEW terminal window with primed OpenCode
REM - Uses full path for Python to avoid PATH issues

echo Starting OpenCode in NEW window...
echo.

REM Use cmd /c start to open a new window - this is critical!
cmd /c "start \"OpenCode Primed\" cmd /k \"cd /d E:\AI-Setup && C:\Users\L5\AppData\Local\Programs\Python\Python311\python.exe launch_opencode_crash_safe.py && C:\Users\L5\AppData\Local\Programs\Python\Python311\python.exe auto_catchup.py\""

echo.
echo If a new window didn't open, double-click this file again.
echo Check E:\AI-Setup\session_logs\ for session history.

pause