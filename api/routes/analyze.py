"""
analyze.py — Pipeline trigger router.
"""

import os
import uuid
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel

from api.auth import get_current_investigator
from recon import db, ingest, fs_recover, classifier, carver, reassemble, validate, relate, prioritize

logger = logging.getLogger(__name__)

router = APIRouter()

class AnalyzeRequest(BaseModel):
    image_path: str
    case_keywords: Optional[List[str]] = None

@router.post("/analyze")
async def analyze_image(
    request: Optional[AnalyzeRequest] = None,
    investigator: Dict[str, Any] = Depends(get_current_investigator)
):
    """
    Triggers full 9-stage EVIDRA recovery pipeline asynchronously.
    Accepts JSON body payload containing image_path and optional case_keywords.
    """
    if not request or not request.image_path:
        raise HTTPException(status_code=400, detail="Must provide JSON payload containing image_path")

    image_path = request.image_path
    case_keywords = request.case_keywords or []
    
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail=f"Image file not found: {image_path}")

    case_id = str(uuid.uuid4())
    case_dir = os.path.join(".", "cases", case_id)
    os.makedirs(case_dir, exist_ok=True)
    db_path = os.path.join(case_dir, "case.db")

    # Run blocking pipeline in threadpool
    try:
        res = await asyncio.to_thread(_run_pipeline, image_path, db_path, case_keywords, investigator['id'])
        res['case_id'] = case_id
        return res
    except Exception as e:
        logger.error(f"Pipeline execution error for case {case_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")

@router.post("/analyze/upload")
async def analyze_upload(
    file: UploadFile = File(...),
    investigator: Dict[str, Any] = Depends(get_current_investigator)
):
    """Triggers analysis pipeline from direct multipart file upload."""
    case_id = str(uuid.uuid4())
    case_dir = os.path.join(".", "cases", case_id)
    os.makedirs(case_dir, exist_ok=True)
    db_path = os.path.join(case_dir, "case.db")
    
    image_path = os.path.join(case_dir, file.filename)
    with open(image_path, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        res = await asyncio.to_thread(_run_pipeline, image_path, db_path, [], investigator['id'])
        res['case_id'] = case_id
        return res
    except Exception as e:
        logger.error(f"Pipeline execution error for uploaded case {case_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")

def _run_pipeline(image_path: str, db_path: str, case_keywords: List[str], investigator_id: str) -> Dict[str, Any]:
    """Executes stages synchronously inside background thread."""
    db.init_db(db_path)
    
    # 1. Ingest
    handle = ingest.open_image(image_path)
    db.upsert_meta(db_path, "image_sha256", handle.sha256)
    db.upsert_meta(db_path, "image_path", image_path)
    db.upsert_meta(db_path, "investigator_id", investigator_id)
    
    # 2. FS Recover
    fs_recover.recover_fs(image_path, db_path)
    
    # 3. Classify (If model exists, or mock)
    model_path = os.environ.get("MODEL_PATH", "./models/block_clf.txt")
    if os.path.exists(model_path):
        model = classifier.load(model_path)
        classifier.classify_image_blocks(model, handle, db_path)
        
    # 4. Carver
    carver.carve(image_path, db_path)
    
    # 5. Reassemble
    reassemble.run_reassembly(db_path, image_path)
    
    # 6. Validate & Relate & Prioritize
    relate.build_relationships(db_path)
    artifacts = prioritize.prioritize_all(db_path, case_keywords)
    
    ingest.close_image(handle)
    
    return {
        'sha256': handle.sha256,
        'blocks_analyzed': handle.size_bytes // handle.block_size,
        'artifacts_found': len(artifacts),
        'status': 'complete'
    }
