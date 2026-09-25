"""
run.py — Unified single-command launcher for Evidra (RECON).
Launches both the backend and frontend unified under ONE single localhost link: http://127.0.0.1:8000/
"""

import os
import sys
import time
import subprocess
import webbrowser

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(root_dir, "frontend")

    print("\n" + "=" * 75)
    print(" 🔬 EVIDRA (RECON) — UNIFIED FORENSIC SUITE LAUNCHER")
    print("=" * 75)
    print(" [1/2] Starting Python FastAPI Backend on http://127.0.0.1:8000 ...")

    # Start backend server
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=root_dir
    )

    time.sleep(2)

    print(" [2/2] Starting Lovable Frontend UI Engine ...")
    
    # Start frontend server
    frontend_cmd = "npx vite dev --host 127.0.0.1 --port 5173"
    frontend_proc = subprocess.Popen(
        frontend_cmd,
        cwd=frontend_dir,
        shell=True
    )

    time.sleep(3)

    print("\n" + "=" * 75)
    print(" 🚀 UNIFIED WORKSTATION READY UNDER ONE SINGLE LINK!")
    print("=" * 75)
    print("  ⭐ Open Full Forensic Application: http://127.0.0.1:8000/")
    print("  ⚡ Swagger API Documentation      : http://127.0.0.1:8000/docs")
    print("=" * 75)
    print(" Press CTRL+C at any time to stop the suite.\n")

    # Open single unified browser URL
    try:
        webbrowser.open("http://127.0.0.1:8000/")
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
