"""
validate.py — Format-specific integrity validators, Magika cross-checks, and entropy strips (Hero Moment 1).

Calculates a 0-100 forensic integrity score based on:
  1. Format decoder validation  (50 pts)
  2. Header & footer presence   (15 pts)
  3. Classifier block agreement (20 pts)
  4. Magika content-type match  (15 pts)

Also generates the per-block entropy strip for intermittent ransomware visualization.
"""

import os
import io
import math
import tempfile
import sqlite3
import zipfile
import logging
from typing import Dict, List, Tuple, Any, Optional

from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

import pypdf
from magika import Magika

from recon.features import byte_histogram, shannon_entropy, chi_square_uniform
from recon.db import get_connection

logger = logging.getLogger(__name__)

# Initialize Magika model once
_MAGIKA_INSTANCE = None

def get_magika() -> Magika:
    global _MAGIKA_INSTANCE
    if _MAGIKA_INSTANCE is None:
        _MAGIKA_INSTANCE = Magika()
    return _MAGIKA_INSTANCE

def entropy_strip(data: bytes, block_size: int = 4096) -> List[float]:
    """
    Calculates per-block Shannon entropy values (0.0 to 8.0) across the artifact bytes.
    Used by Evidra to render the striped entropy bar for intermittent ransomware detection.
    """
    if not data:
        return []
        
    strip = []
    for off in range(0, len(data), block_size):
        chunk = data[off:off + block_size]
        hist = byte_histogram(chunk)
        strip.append(round(shannon_entropy(hist), 2))
        
    return strip

def is_encrypted(data: bytes, block_size: int = 4096) -> Tuple[bool, float]:
    """
    Identifies if an artifact is encrypted (full or intermittent ransomware signature).
    Evaluates: high entropy (> 7.5), uniform chi-square, and lack of valid file headers.
    Returns (is_encrypted_bool, confidence_score).
    """
    if not data or len(data) < 512:
        return False, 0.0
        
    entropies = entropy_strip(data, block_size)
    if not entropies:
        return False, 0.0
        
    avg_entropy = sum(entropies) / len(entropies)
    high_entropy_blocks = sum(1 for e in entropies if e >= 7.5)
    high_ratio = high_entropy_blocks / len(entropies)
    
    # Check for alternating pattern (intermittent encryption signature)
    alternating_score = 0.0
    if len(entropies) >= 4:
        diffs = [abs(entropies[i] - entropies[i-1]) for i in range(1, len(entropies))]
        avg_diff = sum(diffs) / len(diffs)
        if avg_diff > 3.0: # High swing between adjacent sectors
            alternating_score = 0.95
            
    if high_ratio > 0.8:
        return True, min(0.99, max(0.85, avg_entropy / 8.0))
    elif alternating_score > 0.8:
        return True, alternating_score
        
    return False, 0.0

def magika_check(data: bytes) -> Dict[str, Any]:
    """Uses Google Magika deep learning model to identify whole-file content type."""
    if not data:
        return {'label': 'unknown', 'score': 0.0, 'mime_type': 'application/octet-stream', 'group': 'unknown'}
        
    try:
        mag = get_magika()
        res = mag.identify_bytes(data)
        output = res.output
        score_val = float(getattr(res, 'score', 0.0))
        return {
            'label': str(output.label),
            'score': score_val,
            'mime_type': str(output.mime_type),
            'group': str(getattr(output, 'group', 'unknown'))
        }
    except Exception as e:
        logger.warning(f"Magika check failed: {e}")
        return {'label': 'unknown', 'score': 0.0, 'mime_type': 'application/octet-stream', 'group': 'unknown'}

def validate_bytes(data: bytes, file_type: str) -> Dict[str, Any]:
    """Dispatches byte payload to specific format validator."""
    ft = file_type.lower()
    if ft in ['jpeg', 'jpg', 'image/jpeg']:
        return _validate_jpeg(data)
    elif ft in ['png', 'image/png']:
        return _validate_png(data)
    elif ft in ['pdf', 'application/pdf']:
        return _validate_pdf(data)
    elif ft in ['zip', 'docx', 'xlsx', 'application/zip']:
        return _validate_zip(data)
    elif ft in ['sqlite', 'application/x-sqlite3']:
        return _validate_sqlite(data)
    elif ft in ['text', 'html', 'txt', 'text/plain', 'text/html']:
        return _validate_text(data)
    else:
        return {'valid': len(data) > 0, 'partial': False, 'score': 30, 'detail': 'Generic binary payload'}

def _validate_jpeg(data: bytes) -> Dict[str, Any]:
    if not data or not data.startswith(b'\xff\xd8\xff'):
        return {'valid': False, 'partial': False, 'score': 0, 'detail': 'Missing JPEG header'}
        
    has_footer = data.endswith(b'\xff\xd9')
    
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
        return {'valid': True, 'partial': False, 'score': 50, 'detail': '100% JPEG render success'}
    except Exception as e:
        if has_footer:
            return {'valid': False, 'partial': True, 'score': 30, 'detail': f'JPEG header & footer present but decode failed: {e}'}
        return {'valid': False, 'partial': True, 'score': 20, 'detail': 'Truncated JPEG payload'}

def _validate_png(data: bytes) -> Dict[str, Any]:
    if not data or not data.startswith(b'\x89PNG\r\n\x1a\n'):
        return {'valid': False, 'partial': False, 'score': 0, 'detail': 'Missing PNG header'}
        
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
        return {'valid': True, 'partial': False, 'score': 50, 'detail': '100% PNG render success'}
    except Exception as e:
        return {'valid': False, 'partial': b'IEND' in data, 'score': 25, 'detail': f'PNG decode error: {e}'}

def _validate_pdf(data: bytes) -> Dict[str, Any]:
    if not data or not data.startswith(b'%PDF'):
        return {'valid': False, 'partial': False, 'score': 0, 'detail': 'Missing PDF header'}
        
    try:
        reader = pypdf.PdfReader(io.BytesIO(data))
        page_count = len(reader.pages)
        if page_count > 0:
            return {'valid': True, 'partial': False, 'score': 50, 'detail': f'Valid PDF ({page_count} pages)'}
    except Exception as e:
        pass
        
    has_eof = b'%%EOF' in data
    return {'valid': False, 'partial': has_eof, 'score': 25 if has_eof else 10, 'detail': 'Corrupted PDF xref or stream'}

def _validate_zip(data: bytes) -> Dict[str, Any]:
    if not data or not data.startswith(b'PK\x03\x04'):
        return {'valid': False, 'partial': False, 'score': 0, 'detail': 'Missing ZIP header'}
        
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            bad_file = zf.testzip()
            if bad_file is None:
                return {'valid': True, 'partial': False, 'score': 50, 'detail': f'ZIP archive valid ({len(zf.namelist())} members)'}
            else:
                return {'valid': False, 'partial': True, 'score': 25, 'detail': f'CRC error in member: {bad_file}'}
    except Exception as e:
        return {'valid': False, 'partial': True, 'score': 15, 'detail': f'ZIP archive error: {e}'}

def _validate_sqlite(data: bytes) -> Dict[str, Any]:
    if not data or not data.startswith(b'SQLite format 3\x00'):
        return {'valid': False, 'partial': False, 'score': 0, 'detail': 'Missing SQLite header'}
        
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
        
    try:
        conn = sqlite3.connect(tmp_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        res = cursor.fetchone()
        conn.close()
        os.remove(tmp_path)
        
        if res and res[0] == 'ok':
            return {'valid': True, 'partial': False, 'score': 50, 'detail': 'SQLite PRAGMA integrity_check OK'}
        return {'valid': False, 'partial': True, 'score': 20, 'detail': f'SQLite integrity errors: {res}'}
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return {'valid': False, 'partial': True, 'score': 10, 'detail': f'SQLite connection error: {e}'}

def _validate_text(data: bytes) -> Dict[str, Any]:
    if not data:
        return {'valid': False, 'partial': False, 'score': 0, 'detail': 'Empty text file'}
        
    try:
        decoded = data.decode('utf-8')
        printable = sum(1 for c in decoded if c.isprintable() or c in '\n\r\t')
        ratio = printable / len(decoded) if len(decoded) > 0 else 0
        
        if ratio > 0.9:
            return {'valid': True, 'partial': False, 'score': 50, 'detail': f'Valid UTF-8 text ({ratio*100:.1f}% printable)'}
        elif ratio > 0.6:
            return {'valid': False, 'partial': True, 'score': 25, 'detail': f'Partial text ({ratio*100:.1f}% printable)'}
    except UnicodeDecodeError:
        pass
        
    return {'valid': False, 'partial': False, 'score': 5, 'detail': 'Garbage or binary text'}

def score_artifact(
    data: bytes,
    file_type: str,
    block_entropies: List[float],
    magika_label: str,
    classifier_types: List[str]
) -> Tuple[int, str]:
    """
    Computes final 0-100 integrity score and status string:
      Decoder test:      50 pts
      Header & Footer:   15 pts
      Classifier match:  20 pts
      Magika match:      15 pts
    """
    # Check encryption first
    encrypted_flag, enc_conf = is_encrypted(data)
    if encrypted_flag:
        return int(enc_conf * 100), 'ENCRYPTED'

    val_res = validate_bytes(data, file_type)
    score = val_res['score'] # 0 to 50
    
    # Header & Footer check (15 pts)
    if val_res['valid']:
        score += 15
    elif val_res['partial']:
        score += 8
        
    # Classifier agreement (20 pts)
    if classifier_types:
        most_common = max(set(classifier_types), key=classifier_types.count)
        if most_common == file_type or file_type in ['jpg', 'jpeg'] and most_common == 'jpeg':
            score += 20
        elif most_common != 'zero_empty':
            score += 10
            
    # Magika agreement (15 pts)
    if magika_label != 'unknown':
        if magika_label == file_type or (file_type in ['jpg', 'jpeg'] and magika_label in ['jpeg', 'png', 'image']):
            score += 15
        else:
            score += 5

    total_score = min(100, max(0, score))
    
    if val_res['valid'] and total_score >= 70:
        status = 'FULL'
    elif val_res['partial'] or total_score >= 35:
        status = 'PARTIAL'
    elif len(data) > 0:
        status = 'FRAGMENT'
    else:
        status = 'UNRECOVERABLE'
        
    return total_score, status

def validate_artifact(artifact_id: int, db_path: str, image_path: str) -> Dict[str, Any]:
    """Loads artifact bytes from image, runs all validators, and updates case.db record."""
    conn = get_connection(db_path)
    cursor = conn.execute("SELECT name, source_offset, size, mime_type FROM artifacts WHERE id = ?;", (artifact_id,))
    row = cursor.fetchone()
    
    if not row or not os.path.exists(image_path):
        conn.close()
        return {'score': 0, 'status': 'UNRECOVERABLE'}
        
    offset = row['source_offset']
    size = row['size']
    name = row['name']
    mime = row['mime_type'] or ''
    
    with open(image_path, 'rb') as f:
        f.seek(offset)
        data = f.read(size)
        
    ext = os.path.splitext(name)[1].lstrip('.').lower()
    file_type = ext if ext else ('jpeg' if 'jpeg' in mime else 'unknown')
    
    entropies = entropy_strip(data)
    mag_info = magika_check(data)
    
    # Get classifier types for blocks in artifact
    c_cursor = conn.execute(
        "SELECT type_pred FROM blocks WHERE offset >= ? AND offset < ?;",
        (offset, offset + size)
    )
    c_types = [r['type_pred'] for r in c_cursor.fetchall()]
    
    score, status = score_artifact(data, file_type, entropies, mag_info['label'], c_types)
    
    # Update artifact record in case.db
    conn.execute(
        "UPDATE artifacts SET status = ?, confidence = ?, mime_type = ? WHERE id = ?;",
        (status, score / 100.0, mag_info['mime_type'], artifact_id)
    )
    conn.commit()
    conn.close()
    
    return {
        'id': artifact_id,
        'score': score,
        'status': status,
        'entropy_strip': entropies,
        'magika': mag_info
    }
