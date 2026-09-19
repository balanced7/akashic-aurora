@echo off
REM ---------------------------------------------------------------------------------------------
REM launch_rill.cmd -- DOUBLE-CLICKABLE entry point for Rill (the DSH seat).
REM
REM Why a wrapper exists at all: a .ps1 is not double-clickable (Windows opens it in an editor) and
REM a double-clicked .ps1 can also be blocked by ExecutionPolicy. This only exists to hand off to
REM the one script that binds identity -- there is deliberately no logic here, so there is exactly
REM ONE place where the seat's name is decided.
REM
REM Usage:
REM   double-click                 bring Rill up (or open the seat already running)
REM   launch_rill.cmd -New         force a fresh session on another port
REM   launch_rill.cmd -Check       report identity + plugin + port, start nothing
REM   launch_rill.cmd -Foreground  run in this window (closing it stops the seat)
REM ---------------------------------------------------------------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch_rill.ps1" %*

REM Keep the window open when this was a double-click with no arguments, so the receipt above is
REM readable instead of vanishing. Scripted calls (any argument) do not pause.
if "%~1"=="" (
    echo.
    pause
)
