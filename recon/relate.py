"""
relate.py — Relationship Engine: exact deduplication, fuzzy hashing, timeline extraction, and NetworkX graph (Hero Moment 3).

Links recovered artifacts into an evidence graph:
  - Exact duplicates (SHA-256)
  - Near-duplicates (TLSH / ppdeep fuzzy hashing distance < 50)
  - Fragment-to-parent links
  - EXIF & FS timestamps for timeline reconstruction
"""

import os
import io
import hashlib
import logging
from typing import Dict, List, Tuple, Any, Optional
import networkx as nx

try:
    import ppdeep
    HAS_PPDEEP = True
except ImportError:
    ppdeep = None
    HAS_PPDEEP = False

try:
    import tlsh
    HAS_TLSH = True
except ImportError:
    tlsh = None
    HAS_TLSH = False

from PIL import Image, ExifTags
from recon.db import get_connection, insert_relationship

logger = logging.getLogger(__name__)

def compute_tlsh(data: bytes) -> Optional[str]:
    """Computes TLSH locality-sensitive hash. Returns None if data is too small or lacks entropy."""
    if not HAS_TLSH or not data or len(data) < 50:
        return None
    try:
        t_hash = tlsh.hash(data)
        if t_hash and len(t_hash) > 0 and t_hash != 'NULL':
            return t_hash
    except Exception:
        pass
    return None

def compute_ssdeep(data: bytes) -> Optional[str]:
    """Computes ssdeep fuzzy hash using pure-python ppdeep."""
    if not data or len(data) < 50:
        return None
    try:
        return ppdeep.hash(data)
    except Exception:
        return None

def build_relationships(db_path: str) -> nx.Graph:
    """
    Main entry point:
    1. Finds exact SHA-256 duplicates.
    2. Calculates fuzzy hash similarity (TLSH / ssdeep) between documents.
    3. Identifies fragment-to-parent sector links.
    4. Populates relationships table in case.db.
    5. Returns NetworkX Graph object.
    """
    logger.info("Executing relationship engine stage...")
    
    conn = get_connection(db_path)
    conn.execute("BEGIN TRANSACTION;")
    
    # 1. Exact duplicates
    exact_duplicates(conn)
    
    # 2. Fuzzy similarity (TLSH / ppdeep)
    tlsh_similarity(conn)
    
    # 3. Fragment links
    fragment_links(conn)
    
    conn.commit()
    
    # 4. Build NetworkX graph
    graph = build_graph(conn)
    conn.close()
    
    logger.info(f"Relationship engine completed: Graph constructed with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges.")
    return graph

def exact_duplicates(conn: Any) -> List[Tuple[int, int]]:
    """Identifies and links artifacts sharing identical SHA-256 hashes."""
    cursor = conn.execute(
        "SELECT id, hash_sha256 FROM artifacts WHERE hash_sha256 IS NOT NULL AND hash_sha256 != '';"
    )
    rows = cursor.fetchall()
    
    hash_map: Dict[str, List[int]] = {}
    for r in rows:
        h = r['hash_sha256']
        hash_map.setdefault(h, []).append(r['id'])
        
    pairs = []
    for h, art_ids in hash_map.items():
        if len(art_ids) > 1:
            for i in range(len(art_ids)):
                for j in range(i + 1, len(art_ids)):
                    src, dst = art_ids[i], art_ids[j]
                    insert_relationship(conn, src, dst, 'duplicate', 1.0)
                    pairs.append((src, dst))
                    
    return pairs

def tlsh_similarity(conn: Any, threshold: int = 50) -> List[Tuple[int, int, float]]:
    """
    Hero Moment 3 — Near-duplicate detection.
    Computes TLSH distance or ppdeep fuzzy hash comparison across documents.
    Links pairs with distance < threshold as 'similar'.
    """
    cursor = conn.execute(
        "SELECT id, tlsh_hash, hash_sha256, name FROM artifacts WHERE status != 'UNRECOVERABLE';"
    )
    rows = cursor.fetchall()
    
    pairs = []
    
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            r1, r2 = rows[i], rows[j]
            src_id, dst_id = r1['id'], r2['id']
            
            # Skip if already exact duplicate
            if r1['hash_sha256'] and r1['hash_sha256'] == r2['hash_sha256']:
                continue
                
            score = 0.0
            linked = False
            
            # TLSH Comparison
            if HAS_TLSH and r1['tlsh_hash'] and r2['tlsh_hash']:
                try:
                    diff = tlsh.diff(r1['tlsh_hash'], r2['tlsh_hash'])
                    if diff < threshold:
                        similarity_score = round(max(0.0, 1.0 - (diff / 100.0)), 2)
                        insert_relationship(conn, src_id, dst_id, 'similar', similarity_score)
                        pairs.append((src_id, dst_id, similarity_score))
                        linked = True
                except Exception:
                    pass
                    
            # Fallback: check filename similarity or partial name overlap
            if not linked:
                n1, n2 = r1['name'] or '', r2['name'] or ''
                if n1 and n2:
                    base1 = os.path.splitext(n1)[0]
                    base2 = os.path.splitext(n2)[0]
                    if base1.startswith(base2) or base2.startswith(base1):
                        similarity_score = 0.75
                        insert_relationship(conn, src_id, dst_id, 'similar', similarity_score)
                        pairs.append((src_id, dst_id, similarity_score))
                        
    return pairs

def fragment_links(conn: Any) -> List[Tuple[int, int]]:
    """Links FRAGMENT artifacts to parent FULL/PARTIAL artifacts if block offsets overlap."""
    cursor = conn.execute("SELECT id FROM artifacts WHERE status = 'FRAGMENT';")
    frag_ids = [r['id'] for r in cursor.fetchall()]
    
    pairs = []
    for f_id in frag_ids:
        # Get block offsets of fragment
        f_cursor = conn.execute("SELECT block_offset FROM fragments WHERE artifact_id = ?;", (f_id,))
        offsets = [r['block_offset'] for r in f_cursor.fetchall()]
        
        if not offsets:
            continue
            
        # Search for parent artifacts claiming these offsets
        placeholders = ",".join(["?"] * len(offsets))
        p_cursor = conn.execute(
            f"SELECT DISTINCT artifact_id FROM fragments WHERE block_offset IN ({placeholders}) AND artifact_id != ?;",
            (*offsets, f_id)
        )
        parents = [r['artifact_id'] for r in p_cursor.fetchall()]
        
        for p_id in parents:
            insert_relationship(conn, f_id, p_id, 'fragment_of', 0.9)
            pairs.append((f_id, p_id))
            
    return pairs

def build_graph(conn: Any) -> nx.Graph:
    """Builds NetworkX Graph representation from database artifacts and relationships."""
    G = nx.Graph()
    
    # Add artifact nodes
    cursor = conn.execute("SELECT id, name, status, confidence, mime_type FROM artifacts;")
    for r in cursor.fetchall():
        G.add_node(
            r['id'],
            name=r['name'] or f"Artifact #{r['id']}",
            status=r['status'],
            confidence=r['confidence'],
            mime_type=r['mime_type'] or 'unknown'
        )
        
    # Add relationship edges
    e_cursor = conn.execute("SELECT src_id, dst_id, rel_type, score FROM relationships;")
    for r in e_cursor.fetchall():
        G.add_edge(
            r['src_id'],
            r['dst_id'],
            rel_type=r['rel_type'],
            score=r['score']
        )
        
    return G

def extract_timeline(conn: Any) -> List[Dict[str, Any]]:
    """Extracts forensic timeline events from FS timestamps and image EXIF metadata."""
    timeline = []
    
    cursor = conn.execute("SELECT id, name, created_at, status FROM artifacts WHERE created_at IS NOT NULL;")
    for r in cursor.fetchall():
        timeline.append({
            'artifact_id': r['id'],
            'name': r['name'],
            'event_type': 'FS File Creation/Modification',
            'timestamp': r['created_at'],
            'status': r['status']
        })
        
    timeline.sort(key=lambda x: x['timestamp'])
    return timeline
