"""
summarize.py — AI Summary Badge Router (Groq Llama 3.3 70B).
"""

import os
import logging
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth import get_current_investigator
from recon import explain, db

logger = logging.getLogger(__name__)

router = APIRouter()

class SummarizeRequest(BaseModel):
    artifact_id: int
    case_id: str

@router.post("/summarize")
async def summarize_artifact_endpoint(
    request: SummarizeRequest,
    investigator: Dict[str, Any] = Depends(get_current_investigator)
):
    """
    Powers the 'AI Summary' badge in the UI:
    Calls Groq Llama 3.3 70B to produce instant document summaries and entity extractions.
    """
    case_dir = os.path.join(".", "cases", request.case_id)
    db_path = os.path.join(case_dir, "case.db")
    
    if not os.path.exists(db_path):
        db_path = os.environ.get("CASE_DB_PATH", "./case.db")
        if not os.path.exists(db_path):
            raise HTTPException(status_code=404, detail=f"Case database not found for case {request.case_id}")

    conn = db.get_connection(db_path)
    cursor = conn.execute("SELECT name, source_offset, size, mime_type FROM artifacts WHERE id = ?;", (request.artifact_id,))
    row = cursor.fetchone()
    
    image_path = db.get_meta(db_path, "image_path")
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Artifact #{request.artifact_id} not found")

    text_payload = ""
    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as f:
            f.seek(row['source_offset'])
            raw_bytes = f.read(min(row['size'], 4000))
            text_payload = raw_bytes.decode("utf-8", errors="ignore")

    res = explain.summarize_artifact(
        text=text_payload,
        file_type=row['mime_type'] or 'unknown',
        artifact_name=row['name'] or f"Artifact_{request.artifact_id}"
    )
    
    res['artifact_id'] = request.artifact_id
    return res
