"""
run.py — Unified single-command launcher for Evidra (RECON).
Launches both the FastAPI backend (Port 8000) and the Lovable Frontend (Port 5173) together in a single process.
"""

import os
import sys
import time
import subprocess
import webbrowser
import signal

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(root_dir, "frontend")

    print("\n" + "=" * 70)
    print(" 🔬 EVIDRA (RECON) — UNIFIED FORENSIC SUITE LAUNCHER")
    print("=" * 70)
    print(" [1/2] Starting Python FastAPI Backend on http://127.0.0.1:8000 ...")

    # Start backend server
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=root_dir
    )

    time.sleep(2)

    print(" [2/2] Starting Lovable Frontend UI on http://127.0.0.1:5173 ...")
    
    # Start frontend server
    frontend_cmd = "npx vite dev --host 127.0.0.1 --port 5173"
    frontend_proc = subprocess.Popen(
        frontend_cmd,
        cwd=frontend_dir,
        shell=True
    )

    time.sleep(3)

    print("\n" + "=" * 70)
    print(" 🚀 BOTH FRONTEND & BACKEND ARE NOW RUNNING TOGETHER!")
    print("=" * 70)
    print("  🎨 Interactive Frontend Workstation : http://127.0.0.1:5173/")
    print("  ⚡ Backend REST API & Swagger Docs   : http://127.0.0.1:8000/docs")
    print("=" * 70)
    print(" Press CTRL+C at any time to stop both servers.\n")

    # Open browser automatically
    try:
        webbrowser.open("http://127.0.0.1:5173/")
    except Exception:
        pass

    try:
        while True:
            time.sleep(1)
            if backend_proc.poll() is not None or frontend_proc.poll() is not None:
                break
    except KeyboardInterrupt:
        print("\n[!] Shutting down Evidra servers...")
    finally:
        try:
            backend_proc.terminate()
        except Exception:
            pass
        try:
            frontend_proc.terminate()
        except Exception:
            pass
        print("[✓] All services stopped cleanly.")

if __name__ == "__main__":
    main()
