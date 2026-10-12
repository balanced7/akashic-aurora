@echo off
rem Drag and drop videos (or folders of videos) onto this file to import them into the media catalog.
rem The files stay where they are and are never changed or copied: the catalog only remembers them
rem (length, every audio track and its name, keyframes, recorded time, linked practice sessions),
rem then makes the 360p analysis proxy, finds the scene cuts and draws the waveforms.
rem Same as typing, from the repo root:  py -m arsenal.media import "<video>"
rem For the quick version (facts only, about a second a file):  py -m arsenal.media import --quick "<video>"
setlocal
cd /d "%~dp0..\.."
if "%~1"=="" (
    echo Drag one or more videos, or a folder of them, onto media-import.cmd to import them.
    echo.
    pause
    exit /b 2
)
set "PYTHONUTF8=1"
set "FAILED=0"
:next
if "%~1"=="" goto done
echo.
py -m arsenal.media import --dropped "%~1"
if errorlevel 1 set "FAILED=1"
shift
goto next
:done
echo.
if "%FAILED%"=="1" (
    echo Some files did not import. Read the messages above.
) else (
    echo All done. Find them with:  py -m arsenal.media find
)
echo.
pause
exit /b %FAILED%
