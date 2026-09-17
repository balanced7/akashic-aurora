@echo off
rem Drag and drop one or more videos onto this file to make TikTok-ready copies.
rem Each copy is saved beside its original as "<name> tiktok.mp4". Originals are never changed.
rem Same as typing, from the repo root:  py -m arsenal tiktok "<video>"
rem (--dropped only changes the wording: a drop cannot add --force, so messages do not suggest it)
setlocal
cd /d "%~dp0..\.."
if "%~1"=="" (
    echo Drag one or more videos onto tiktok-ready.cmd to make TikTok-ready copies.
    echo.
    pause
    exit /b 2
)
set "FAILED=0"
:next
if "%~1"=="" goto done
echo.
py -m arsenal tiktok --dropped "%~1"
if errorlevel 1 set "FAILED=1"
shift
goto next
:done
echo.
if "%FAILED%"=="1" (
    echo Some videos did not finish. Read the messages above.
) else (
    echo All done. The TikTok copies are next to the originals.
)
echo.
pause
exit /b %FAILED%
