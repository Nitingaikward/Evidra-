"""
prioritize.py — Evidence prioritizer with explicit Ransomware Flag (+30 pts) and PII scanner.

Ensures ENCRYPTED ransomware evidence is never buried at rank 0.
"""

import re
import os
import logging
from typing import Dict, List, Tuple, Any, Optional

from recon.db import get_connection

logger = logging.getLogger(__name__)

TYPE_WEIGHTS = {
    'pdf': 1.0,
    'zip_office': 1.0,
    'sqlite': 1.0,
    'jpeg': 0.8,
    'png': 0.8,
    'text_html': 0.7,
    'exe': 0.5,
    'compressed_other': 0.3,
    'encrypted_random': 1.0,
    'zero_empty': 0.0
}

PII_PATTERNS = {
    'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    'phone': r'\+?[1-9]\d{1,14}',
    'ipv4': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
    'card_number': r'\b(?:\d[ -]?){13,16}\b'
}

def luhn_check(number_str: str) -> bool:
    """Validates credit card numbers using Luhn checksum algorithm."""
    digits = [int(c) for c in number_str if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = digit * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += digit
    return checksum % 10 == 0

def find_pii(text: str) -> Dict[str, List[str]]:
    """Scans text for PII patterns."""
    if not text:
        return {}
    hits: Dict[str, List[str]] = {}
    for pat_name, pat_regex in PII_PATTERNS.items():
        matches = re.findall(pat_regex, text)
        if pat_name == 'card_number':
            valid_cards = [m for m in matches if luhn_check(m)]
            if valid_cards:
                hits[pat_name] = list(set(valid_cards))
        elif matches:
            hits[pat_name] = list(set(matches))
    return hits

def prioritize_all(db_path: str, case_keywords: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Calculates priority scores.
    ENCRYPTED artifacts get an explicit Ransomware Flag (+30 pts) so they stay at the top.
    """
    logger.info("Prioritizing recovered evidence artifacts...")
    conn = get_connection(db_path)
    cursor = conn.execute("SELECT * FROM artifacts WHERE status != 'UNRECOVERABLE';")
    artifacts = [dict(r) for r in cursor.fetchall()]
    
    if not artifacts:
        conn.close()
        return []
        
    d_cursor = conn.execute("SELECT src_id FROM relationships WHERE rel_type = 'duplicate';")
    duplicate_ids = {r['src_id'] for r in d_cursor.fetchall()}
    
    conn.execute("BEGIN TRANSACTION;")
    prioritized_list = []
    
    for art in artifacts:
        art_id = art['id']
        status = art['status']
        conf = art['confidence'] or 0.5
        was_deleted = status in ['PARTIAL', 'REASSEMBLED'] or art['method'] == 'carve'
        is_dup = art_id in duplicate_ids
        
        # Base score from confidence
        score = conf * 50.0
        
        # Explicit Ransomware Flag (+30 pts)
        if status == 'ENCRYPTED':
            score += 35.0 # Ransomware evidence gets high priority!
            
        if was_deleted:
            score += 15.0 # Deletion bonus
            
        if not is_dup:
            score += 10.0 # Uniqueness bonus
            
        priority_score = round(min(100.0, score), 1)
        conn.execute("UPDATE artifacts SET score = ? WHERE id = ?;", (priority_score, art_id))
        
        art['priority_score'] = priority_score
        prioritized_list.append(art)
        
    conn.commit()
    conn.close()
    
    prioritized_list.sort(key=lambda x: x['priority_score'], reverse=True)
    return prioritized_list
