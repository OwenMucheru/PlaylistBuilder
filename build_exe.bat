@echo off
REM OmniPlaylist - build a standalone Windows executable with PyInstaller

if not exist .venv (
    echo Virtual environment not found. Run build.bat first.
    exit /b 1
)

call .venv\Scripts\activate.bat

echo Building OmniPlaylist.exe with PyInstaller...
pyinstaller --noconfirm --clean ^
    --name OmniPlaylist ^
    --windowed ^
    --add-data "presets;presets" ^
    --add-data "config.json;." ^
    app.py

echo.
echo Build complete. Find the executable in dist\OmniPlaylist\OmniPlaylist.exe
