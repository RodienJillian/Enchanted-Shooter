@echo off
echo 🎵 Taylor Swift Lyric Guesser - LyricsShooter 🎵
echo.
echo Starting the game servers...
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.8+ and try again.
    pause
    exit /b 1
)

REM Check if Node.js is available
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js not found. Please install Node.js 16+ and try again.
    pause
    exit /b 1
)

echo ✅ Dependencies found. Starting servers...
echo.

REM Start the game using the Python startup script
python start_game.py

pause
