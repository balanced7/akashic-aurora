@echo off
REM One-time Google login for Gemini web + AI Mode (free, not API tokens)
cd /d E:\AI-Setup
py -m pip install -r requirements-gemini-web.txt -q
py -m playwright install chrome
py scripts\gemini_web.py --login
