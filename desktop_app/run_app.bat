@echo off
cd /d "%~dp0"

call "..\.venv\Scripts\activate.bat"

set RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO=0

python app.py
pause