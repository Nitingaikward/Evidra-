"""
artifacts.py — Artifact listing, detail, block hex inspector (Secret Weapon 2), and download endpoints.
"""

import os
import io
import logging
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse

from api.auth import get_current_investigator
from recon import db, validate, features

logger = logging.getLogger(__name__)

router = APIRouter()

def _get_db_path(case_id: str) -> str:
    path = os.path.join(".", "cases", case_id, "case.db")
    if not os.path.exists(path):
        default_path = os.environ.get("CASE_DB_PATH", "./case.db")
        if os.path.exists(default_path):
            return default_path
        raise HTTPException(status_code=404, detail=f"Case database not found for case {case_id}")
    return path

@router.get("/artifacts/{case_id}")
async def list_artifacts(
    case_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    status_filter: Optional[str] = None,
    method_filter: Optional[str] = None,
    investigator: Dict[str, Any] = Depends(get_current_investigator)
):
    """Returns paginated artifact inventory list for case."""
    db_path = _get_db_path(case_id)
    conn = db.get_connection(db_path)
    
    query = "SELECT * FROM artifacts WHERE 1=1"
    params = []
    
    if status_filter:
        query += " AND status = ?"
        params.append(status_filter.upper())
    if method_filter:
        query += " AND method = ?"
        params.append(method_filter.lower())
        
    query += " ORDER BY score DESC LIMIT ? OFFSET ?;"
    params.extend([page_size, (page - 1) * page_size])
    
    cursor = conn.execute(query, params)
    artifacts = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    return {
        'case_id': case_id,
        'page': page,
        'page_size': page_size,
        'artifacts': artifacts
    }

@router.get("/blocks/{case_id}/{offset}")
async def inspect_block(
    case_id: str,
    offset: int,
    investigator: Dict[str, Any] = Depends(get_current_investigator)
):
    """
    Secret Weapon 2:
    Interactive Sector Block Hex & ML Inspector.
    Zero-copy reads raw 4KB bytes from disk image and returns formatted hex dump,
    Shannon entropy, Chi-Square uniformity, and ML prediction confidence.
    """
    db_path = _get_db_path(case_id)
    conn = db.get_connection(db_path)
    
    image_path = db.get_meta(db_path, "image_path")
    cursor = conn.execute("SELECT * FROM blocks WHERE offset = ?;", (offset,))
    block_info = cursor.fetchone()
    conn.close()
    
    if not image_path or not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Disk image file not found")

    with open(image_path, "rb") as f:
        f.seek(offset)
        raw_bytes = f.read(4096)
        
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Invalid sector offset")

    # Generate formatted hex dump string
    hex_dump_lines = []
    for line_idx in range(0, min(512, len(raw_bytes)), 16):
        chunk = raw_bytes[line_idx:line_idx+16]
        hex_str = " ".join([f"{b:02X}" for b in chunk])
        ascii_str = "".join([chr(b) if 32 <= b <= 126 else "." for b in chunk])
        hex_dump_lines.append(f"{line_idx:04X}:  {hex_str:<48}  |{ascii_str}|")

    hist = features.byte_histogram(raw_bytes)
    entropy_val = round(features.shannon_entropy(hist), 2)
    chi_sq_val = round(features.chi_square_uniform(hist, len(raw_bytes)), 2)

    block_data = dict(block_info) if block_info else {'type_pred': 'unknown', 'confidence': 0.0}

    return {
        "case_id": case_id,
        "offset": offset,
        "hex_dump": "\n".join(hex_dump_lines),
        "entropy": entropy_val,
        "chi_square": chi_sq_val,
        "type_pred": block_data.get('type_pred', 'unknown'),
        "confidence": block_data.get('confidence', 0.0),
        "claimed": block_data.get('claimed', 0) == 1
    }

@router.get("/artifacts/{case_id}/{artifact_id}")
async def get_artifact_detail(
    case_id: str,
    artifact_id: int,
    investigator: Dict[str, Any] = Depends(get_current_investigator)
):
    """Returns detailed forensic metadata, entropy strip array, and graph links for an artifact."""
    db_path = _get_db_path(case_id)
    conn = db.get_connection(db_path)
    
    cursor = conn.execute("SELECT * FROM artifacts WHERE id = ?;", (artifact_id,))
    art = cursor.fetchone()
    if not art:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Artifact #{artifact_id} not found")
        
    art_dict = dict(art)
    image_path = db.get_meta(db_path, "image_path")
    
    entropies = []
    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as f:
            f.seek(art_dict['source_offset'])
            data = f.read(art_dict['size'])
            entropies = validate.entropy_strip(data)
            
    # Relationships
    r_cursor = conn.execute("SELECT * FROM relationships WHERE src_id = ? OR dst_id = ?;", (artifact_id, artifact_id))
    relationships = [dict(r) for r in r_cursor.fetchall()]
    
    conn.close()
    
    art_dict['entropy_strip'] = entropies
    art_dict['relationships'] = relationships
    return art_dict

@router.get("/artifacts/{case_id}/{artifact_id}/download")
async def download_artifact_bytes(
    case_id: str,
    artifact_id: int,
    investigator: Dict[str, Any] = Depends(get_current_investigator)
):
    """Streams raw recovered bytes for artifact download."""
    db_path = _get_db_path(case_id)
    conn = db.get_connection(db_path)
    
    cursor = conn.execute("SELECT name, source_offset, size, mime_type FROM artifacts WHERE id = ?;", (artifact_id,))
    row = cursor.fetchone()
    image_path = db.get_meta(db_path, "image_path")
    conn.close()
    
    if not row or not image_path or not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Artifact raw payload not found")
        
    with open(image_path, "rb") as f:
        f.seek(row['source_offset'])
        data = f.read(row['size'])
        
    mime = row['mime_type'] or "application/octet-stream"
    filename = row['name'] or f"artifact_{artifact_id}.bin"
    
    return Response(
        content=data,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
