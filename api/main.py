"""
main.py — FastAPI application entry point for EVIDRA backend with unified Frontend reverse proxy.
Provides BOTH frontend UI and backend API under a single unified localhost link (http://127.0.0.1:8000).
"""

import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

import httpx
from fastapi import FastAPI, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from api.auth import get_current_investigator
from api.routes import analyze, summarize, artifacts, report, comparison
from recon import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("evidra.api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    db_path = os.environ.get("CASE_DB_PATH", "./case.db")
    db.init_db(db_path)
    logger.info("EVIDRA Unified Suite started on http://127.0.0.1:8000")
    yield

app = FastAPI(
    title="EVIDRA Forensic Suite",
    version="0.1.0",
    description="AI-Assisted Data Recovery and Evidence Reconstruction Suite",
    lifespan=lifespan
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core Backend Router mounts
app.include_router(analyze.router, prefix="/api", tags=["Analyze"])
app.include_router(summarize.router, prefix="/api", tags=["AI Summaries"])
app.include_router(artifacts.router, prefix="/api", tags=["Artifacts & Blocks"])
app.include_router(comparison.router, prefix="/api", tags=["Secret Weapon Benchmark Comparison"])
app.include_router(report.router, prefix="/api", tags=["Reports"])

@app.get("/health", tags=["Health"])
def health_check():
    """Public health check endpoint."""
    return {"status": "ok", "version": "0.1.0", "service": "EVIDRA Unified Suite"}

@app.get("/api/me", tags=["Auth"])
def get_me(investigator: dict = Depends(get_current_investigator)):
    """Protected endpoint returning current investigator identity from Supabase JWT."""
    return investigator

# -------------------------------------------------------------------------
# Unified Frontend Gateway (Reverse Proxy to Frontend)
# Allows accessing the complete UI and Backend on the exact same port (8000)
# -------------------------------------------------------------------------
FRONTEND_DEV_URL = os.environ.get("FRONTEND_DEV_URL", "http://127.0.0.1:5173")

@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def reverse_proxy_frontend(request: Request, full_path: str):
    """Seamlessly proxies frontend requests so everything runs under a single port (8000)."""
    # Exclude API and Docs routes
    if full_path.startswith("api") or full_path in ["docs", "openapi.json", "redoc", "health"]:
        return Response(status_code=404, content="Not found")

    target_url = f"{FRONTEND_DEV_URL}/{full_path}"
    if request.url.query:
        target_url += f"?{request.url.query}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            req_headers = {k: v for k, v in request.headers.items() if k.lower() not in ["host", "content-length"]}
            content = await request.body()
            
            resp = await client.request(
                method=request.method,
                url=target_url,
                headers=req_headers,
                content=content,
                follow_redirects=True
            )
            
            excluded_headers = ["content-encoding", "transfer-encoding", "connection"]
            resp_headers = {k: v for k, v in resp.headers.items() if k.lower() not in excluded_headers}
            
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=resp_headers,
                media_type=resp.headers.get("content-type")
            )
    except Exception:
        return HTMLResponse(
            content="""
            <html>
                <head><title>Evidra Forensics</title></head>
                <body style="background:#0b0f19;color:#fff;font-family:sans-serif;padding:40px;text-align:center;">
                    <h2>🔬 Evidra (RECON)</h2>
                    <p style="color:#94a3b8;">Backend is active. Frontend is starting up...</p>
                    <p><a href="http://127.0.0.1:5173" style="color:#6366f1;">Click here to open direct frontend</a></p>
                </body>
            </html>
            """,
            status_code=200
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
