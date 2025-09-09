#!/usr/bin/env python3
"""
Startup script for Taylor Swift Lyric Guesser - LyricsShooter
This script helps you start both the backend and frontend servers.
"""

import subprocess
import sys
import time
import os
import signal
import threading
from pathlib import Path

def print_banner():
    print("🎵" * 50)
    print("🎵 Taylor Swift Lyric Guesser - LyricsShooter 🎵")
    print("🎵" * 50)
    print()

def check_dependencies():
    """Check if required dependencies are available."""
    print("🔍 Checking dependencies...")
    
    # Check Python
    try:
        import fastapi
        print("✅ FastAPI available")
    except ImportError:
        print("❌ FastAPI not found. Please run: pip install -r backend/requirements.txt")
        return False
    
    # Check if backend directory exists
    if not Path("backend").exists():
        print("❌ Backend directory not found")
        return False
    
    # Check if frontend directory exists
    if not Path("frontend").exists():
        print("❌ Frontend directory not found")
        return False
    
    print("✅ All dependencies available")
    return True

def start_backend():
    """Start the FastAPI backend server."""
    print("🚀 Starting backend server...")
    
    backend_dir = Path("backend")
    os.chdir(backend_dir)
    
    try:
        # Start the server
        process = subprocess.Popen([
            sys.executable, "run_server.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a bit for server to start
        time.sleep(3)
        
        if process.poll() is None:
            print("✅ Backend server started successfully on http://localhost:8000")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Backend server failed to start:")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            return None
            
    except Exception as e:
        print(f"❌ Error starting backend: {e}")
        return None

def start_frontend():
    """Start the Svelte frontend development server."""
    print("🌐 Starting frontend server...")
    
    frontend_dir = Path("frontend")
    os.chdir(frontend_dir)
    
    try:
        # Check if node_modules exists
        if not Path("node_modules").exists():
            print("📦 Installing frontend dependencies...")
            subprocess.run(["npm", "install"], check=True)
        
        # Start the dev server
        process = subprocess.Popen([
            "npm", "run", "dev"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a bit for server to start
        time.sleep(5)
        
        if process.poll() is None:
            print("✅ Frontend server started successfully on http://localhost:5173")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Frontend server failed to start:")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            return None
            
    except Exception as e:
        print(f"❌ Error starting frontend: {e}")
        return None

def main():
    """Main function to start both servers."""
    print_banner()
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Please fix the dependency issues and try again.")
        return
    
    print("🎮 Starting LyricsShooter game servers...\n")
    
    # Start backend
    backend_process = start_backend()
    if not backend_process:
        print("❌ Failed to start backend. Exiting.")
        return
    
    # Start frontend
    frontend_process = start_frontend()
    if not frontend_process:
        print("❌ Failed to start frontend. Stopping backend...")
        backend_process.terminate()
        return
    
    print("\n🎉 Both servers started successfully!")
    print("📍 Backend API: http://localhost:8000")
    print("📍 Frontend: http://localhost:5173")
    print("📖 API Docs: http://localhost:8000/docs")
    print("\n🎮 Open http://localhost:5173 in your browser to play!")
    print("\nPress Ctrl+C to stop both servers...")
    
    try:
        # Keep the script running
        while True:
            time.sleep(1)
            
            # Check if processes are still running
            if backend_process.poll() is not None:
                print("❌ Backend server stopped unexpectedly")
                break
                
            if frontend_process.poll() is not None:
                print("❌ Frontend server stopped unexpectedly")
                break
                
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping servers...")
        
        # Stop backend
        if backend_process and backend_process.poll() is None:
            backend_process.terminate()
            print("✅ Backend server stopped")
        
        # Stop frontend
        if frontend_process and frontend_process.poll() is None:
            frontend_process.terminate()
            print("✅ Frontend server stopped")
        
        print("👋 Goodbye! Thanks for playing LyricsShooter! 🎵")

if __name__ == "__main__":
    main()
