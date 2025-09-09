#!/bin/bash

echo "🎵 Taylor Swift Lyric Guesser - LyricsShooter 🎵"
echo
echo "Starting the game servers..."
echo

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "❌ Python not found. Please install Python 3.8+ and try again."
        exit 1
    fi
fi

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 16+ and try again."
    exit 1
fi

echo "✅ Dependencies found. Starting servers..."
echo

# Start the game using the Python startup script
python3 start_game.py 2>/dev/null || python start_game.py
