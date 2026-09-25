"""
reassemble.py — Fragmented file reassembly engine (Hero Moment 2).

Assigns status 'REASSEMBLED' (confidence 0.90) to reconstructed partial files
to prevent false 'FULL' claims when pixels across the splice row are reconstructed.
"""

import os
import io
import math
import logging
from collections import Counter
from typing import Dict, List, Tuple, Any, Optional

from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

from recon.db import get_connection, insert_artifact

logger = logging.getLogger(__name__)

def _jpeg_decode_score(data: bytes) -> float:
    """Measures Pillow JPEG decoding progress fraction (0.0 to 1.0)."""
    if not data or len(data) < 10:
        return 0.0
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
        return 1.0
    except Exception:
        try:
            img = Image.open(io.BytesIO(data))
            width, height = img.size
            if height == 0:
                return 0.0
            return min(0.95, max(0.1, len(data) / (width * height * 3 + 1000)))
        except Exception:
            return 0.0

def _generic_validate(data: bytes, file_type: str) -> bool:
    """Basic format validation check."""
    if not data:
        return False
    if file_type in ['jpeg', 'jpg']:
        return _jpeg_decode_score(data) > 0.9
    elif file_type == 'png':
        return data.startswith(b'\x89PNG\r\n\x1a\n') and b'IEND' in data
    elif file_type == 'pdf':
        return data.startswith(b'%PDF') and b'%%EOF' in data
    elif file_type in ['zip', 'docx', 'xlsx']:
        return data.startswith(b'PK\x03\x04')
    return False

def reassemble_binary(
    artifact_bytes: bytes,
    image_path: str,
    block_preds: Dict[int, str],
    artifact_type: str,
    db_path: str,
    artifact_id: int,
    block_size: int = 4096,
    max_gap: int = 2000
) -> Optional[bytes]:
    """Attempts bifragment gap carving on damaged binary artifacts."""
    if _generic_validate(artifact_bytes, artifact_type):
        return artifact_bytes

    initial_score = _jpeg_decode_score(artifact_bytes) if artifact_type in ['jpeg', 'jpg'] else 0.0
    frag_point_block = len(artifact_bytes) // block_size
    head_bytes = artifact_bytes[:frag_point_block * block_size]
    
    if not head_bytes or not os.path.exists(image_path):
        return None
        
    file_size = os.path.getsize(image_path)
    expected_class = 'jpeg' if artifact_type in ['jpg', 'jpeg'] else 'zip_office'

    best_bytes = artifact_bytes
    best_score = initial_score

    with open(image_path, 'rb') as f:
        start_search_offset = (frag_point_block + 1) * block_size
        
        for gap_blocks in range(1, max_gap + 1):
            candidate_offset = start_search_offset + (gap_blocks * block_size)
            if candidate_offset >= file_size:
                break
                
            pred_class = block_preds.get(candidate_offset, '')
            if pred_class != expected_class and pred_class != '':
                continue
                
            f.seek(candidate_offset)
            tail_chunk = f.read(64 * 1024)
            if not tail_chunk:
                continue
                
            candidate_reassembly = head_bytes + tail_chunk
            
            if artifact_type in ['jpeg', 'jpg']:
                score = _jpeg_decode_score(candidate_reassembly)
                if score > best_score:
                    best_score = score
                    best_bytes = candidate_reassembly
                    if score >= 0.95:
                        break
            else:
                if _generic_validate(candidate_reassembly, artifact_type):
                    return candidate_reassembly

    return best_bytes if best_score > initial_score else None

def run_reassembly(db_path: str, image_path: str, block_size: int = 4096) -> int:
    """Updates PARTIAL artifacts to status 'REASSEMBLED' (confidence 0.90) upon gap restoration."""
    logger.info("Executing reassembly pipeline stage...")
    conn = get_connection(db_path)
    
    cursor = conn.execute("SELECT offset, type_pred FROM blocks;")
    block_preds = {row['offset']: row['type_pred'] for row in cursor.fetchall()}
    
    cursor = conn.execute("SELECT id, name, source_offset, size, mime_type FROM artifacts WHERE status = 'PARTIAL';")
    partials = cursor.fetchall()
    conn.close()
    
    if not partials or not os.path.exists(image_path):
        return 0
        
    improved_count = 0
    with open(image_path, 'rb') as f:
        for row in partials:
            art_id = row['id']
            offset = row['source_offset']
            size = row['size']
            name = row['name']
            mime = row['mime_type'] or ''
            
            f.seek(offset)
            data = f.read(size)
            file_type = 'jpeg' if 'image/jpeg' in mime or name.endswith(('.jpg', '.jpeg')) else 'unknown'
            
            restored = reassemble_binary(
                artifact_bytes=data,
                image_path=image_path,
                block_preds=block_preds,
                artifact_type=file_type,
                db_path=db_path,
                artifact_id=art_id,
                block_size=block_size
            )
            
            if restored and len(restored) > size:
                improved_count += 1
                conn = get_connection(db_path)
                conn.execute(
                    "UPDATE artifacts SET status = 'REASSEMBLED', size = ?, method = 'reassembled', confidence = 0.90 WHERE id = ?;",
                    (len(restored), art_id)
                )
                conn.commit()
                conn.close()
                logger.info(f"Updated artifact {art_id} ({name}) to REASSEMBLED status.")
                
    return improved_count
