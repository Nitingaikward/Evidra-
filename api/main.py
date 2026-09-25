"""
main.py — FastAPI application entry point for EVIDRA backend.
"""

import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

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
    logger.info("EVIDRA API server started successfully.")
    yield

app = FastAPI(
    title="EVIDRA API",
    version="0.1.0",
    description="AI-Assisted Data Recovery and Evidence Reconstruction API",
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

# Router mounts
app.include_router(analyze.router, prefix="/api", tags=["Analyze"])
app.include_router(summarize.router, prefix="/api", tags=["AI Summaries"])
app.include_router(artifacts.router, prefix="/api", tags=["Artifacts & Blocks"])
app.include_router(comparison.router, prefix="/api", tags=["Secret Weapon Benchmark Comparison"])
app.include_router(report.router, prefix="/api", tags=["Reports"])

@app.get("/health", tags=["Health"])
def health_check():
    """Public health check endpoint."""
    return {"status": "ok", "version": "0.1.0", "service": "EVIDRA Backend API"}

@app.get("/api/me", tags=["Auth"])
def get_me(investigator: dict = Depends(get_current_investigator)):
    """Protected endpoint returning current investigator identity from Supabase JWT."""
    return investigator

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
