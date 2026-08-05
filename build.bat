@echo off
REM OmniPlaylist - local development setup (Windows)
REM Creates a virtual environment and installs dependencies.

echo Creating virtual environment...
python -m venv .venv

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Done. Run the app with:
echo   .venv\Scripts\activate.bat ^&^& python app.py
