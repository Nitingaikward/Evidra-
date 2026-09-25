"""
run.py — Unified single-command launcher for Evidra (RECON).
Launches both backend & frontend under ONE single localhost link: http://127.0.0.1:8000/
"""

import os
import sys
import time
import subprocess
import webbrowser

# Ensure UTF-8 output on Windows consoles
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(root_dir, "frontend")

    print("\n" + "=" * 75)
    print(" [EVIDRA RECON] - UNIFIED FORENSIC SUITE LAUNCHER")
    print("=" * 75)

    # 1. Start Python FastAPI Backend
    print(" [1/2] Starting Python FastAPI Backend on http://127.0.0.1:8000 ...")
    backend_cmd = [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000"]
    backend_proc = subprocess.Popen(
        backend_cmd,
        cwd=root_dir
    )

    time.sleep(2)

    # 2. Start Frontend UI
    print(" [2/2] Starting Frontend UI Engine ...")
    is_windows = sys.platform.startswith("win")
    npm_cmd = "npm.cmd run dev -- --host 127.0.0.1 --port 5173" if is_windows else "npm run dev -- --host 127.0.0.1 --port 5173"

    frontend_proc = subprocess.Popen(
        npm_cmd,
        cwd=frontend_dir,
        shell=True
    )

    time.sleep(3)

    print("\n" + "=" * 75)
    print(" >> UNIFIED WORKSTATION READY UNDER ONE SINGLE LINK!")
    print("=" * 75)
    print("  * Open Full Forensic Application: http://127.0.0.1:8000/")
    print("  * Swagger API Documentation      : http://127.0.0.1:8000/docs")
    print("=" * 75)
    print(" Press CTRL+C in this terminal at any time to stop the suite.\n")

    # Automatically open browser
    try:
        webbrowser.open("http://127.0.0.1:8000/")
    except Exception:
        pass

    try:
        while True:
            time.sleep(1)
            if backend_proc.poll() is not None:
                print("\n[!] Backend process stopped.")
                break
            if frontend_proc.poll() is not None:
                print("\n[!] Frontend process stopped.")
                break
    except KeyboardInterrupt:
        print("\n[!] Shutting down Evidra suite...")
    finally:
        try:
            backend_proc.terminate()
        except Exception:
            pass
        try:
            frontend_proc.terminate()
        except Exception:
            pass
        print("[OK] All services stopped cleanly.")

if __name__ == "__main__":
    main()
