"""
report.py — Report download endpoints.
"""

import os
import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse

from api.auth import get_current_investigator
from recon import report

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/report/{case_id}")
async def get_report(
    case_id: str,
    format: str = Query("html", regex="^(html|json)$"),
    investigator: Dict[str, Any] = Depends(get_current_investigator)
):
    """Generates and downloads JSON or HTML forensic reports."""
    case_dir = os.path.join(".", "cases", case_id)
    db_path = os.path.join(case_dir, "case.db")
    
    if not os.path.exists(db_path):
        db_path = os.environ.get("CASE_DB_PATH", "./case.db")
        if not os.path.exists(db_path):
            raise HTTPException(status_code=404, detail=f"Case database not found for case {case_id}")

    if format == "json":
        json_path = os.path.join(case_dir, "report.json")
        report.generate_json(db_path, json_path)
        return FileResponse(json_path, media_type="application/json", filename=f"evidra_report_{case_id}.json")
    else:
        html_path = os.path.join(case_dir, "report.html")
        report.generate_html(db_path, html_path)
        return FileResponse(html_path, media_type="text/html", filename=f"evidra_report_{case_id}.html")
