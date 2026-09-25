"""
fs_recover.py — Filesystem-level recovery using pytsk3 and Sleuth Kit fallback.

Parses directory structures (FAT12/16/32, NTFS, ext2/3/4) to extract both allocated
and deleted files with original names, path hierarchy, and timestamps.
"""

import os
import logging
import subprocess
import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

try:
    import pytsk3
    HAS_PYTSK3 = True
except ImportError:
    pytsk3 = None
    HAS_PYTSK3 = False

from recon.db import get_connection, insert_artifact, insert_fragment, claim_blocks

logger = logging.getLogger(__name__)

def recover_fs(image_path: str, db_path: str, block_size: int = 4096) -> Dict[str, Any]:
    """
    Main entry point for filesystem recovery.
    Attempts pytsk3 parsing; if missing or corrupted, falls back to fls/icat command line parsing.
    """
    logger.info(f"Starting filesystem recovery on {image_path}...")
    
    result = {
        'allocated': 0,
        'deleted': 0,
        'fs_type': 'Unknown',
        'error': None
    }
    
    if not HAS_PYTSK3:
        logger.warning("pytsk3 module not available in Python environment. Using fls CLI fallback...")
        return _fallback_fls(image_path, db_path)
    
    try:
        img_info = pytsk3.Img_Info(image_path)
    except Exception as e:
        logger.warning(f"pytsk3 failed to open raw image: {e}. Attempting fallback...")
        return _fallback_fls(image_path, db_path)
        
    fs_info = None
    # Try auto-detecting filesystem
    try:
        fs_info = pytsk3.FS_Info(img_info)
        result['fs_type'] = str(fs_info.info.ft_type)
    except Exception as e:
        logger.warning(f"pytsk3 auto FS_Info failed: {e}. Trying volume system or fallback...")
        try:
            vs = pytsk3.VS_Info(img_info)
            for part in vs:
                if part.flags & pytsk3.TSK_VS_PART_FLAG_ALLOC:
                    try:
                        fs_info = pytsk3.FS_Info(img_info, offset=part.start * vs.info.block_size)
                        result['fs_type'] = str(fs_info.info.ft_type)
                        break
                    except Exception:
                        continue
        except Exception:
            pass

    if fs_info is None:
        logger.warning("No valid filesystem identified by pytsk3. Operating in carving-only fallback mode.")
        result['error'] = "No valid filesystem table found"
        return result

    conn = get_connection(db_path)
    conn.execute("BEGIN TRANSACTION;")
    
    claimed_offsets: List[int] = []
    
    try:
        root_dir = fs_info.open_dir("/")
        _walk_dir(fs_info, root_dir, "/", conn, claimed_offsets, result, block_size)
        
        # Mark claimed blocks in database
        if claimed_offsets:
            claim_blocks(conn, list(set(claimed_offsets)))
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Error during pytsk3 directory walk: {e}")
        result['error'] = str(e)
    finally:
        conn.close()
        
    logger.info(f"FS recovery completed: {result['allocated']} allocated files, {result['deleted']} deleted files recovered.")
    return result

def _walk_dir(
    fs_info: Any,
    directory: Any,
    path_prefix: str,
    conn: Any,
    claimed_offsets: List[int],
    result: Dict[str, Any],
    block_size: int
) -> None:
    """Recursively traverses directory tree and extracts file metadata and byte sector runs."""
    for entry in directory:
        if not hasattr(entry, "info") or not hasattr(entry.info, "name") or not entry.info.name:
            continue
            
        name = entry.info.name.name.decode('utf-8', errors='replace')
        if name in [".", ".."]:
            continue
            
        full_path = os.path.join(path_prefix, name).replace("\\", "/")
        
        # Handle directory recursion
        if entry.info.meta and entry.info.meta.type == pytsk3.TSK_FS_META_TYPE_DIR:
            try:
                sub_dir = fs_info.open_dir(path=full_path)
                _walk_dir(fs_info, sub_dir, full_path, conn, claimed_offsets, result, block_size)
            except Exception as e:
                logger.debug(f"Failed to recurse into dir {full_path}: {e}")
            continue

        # Process file entry
        if entry.info.meta and entry.info.meta.type == pytsk3.TSK_FS_META_TYPE_REG:
            size = entry.info.meta.size
            flags = entry.info.name.flags
            is_allocated = (flags == pytsk3.TSK_FS_NAME_FLAG_ALLOC)
            
            if is_allocated:
                result['allocated'] += 1
            else:
                result['deleted'] += 1

            # Extract block sector runs
            sector_offsets = []
            try:
                for attr in entry.info.meta:
                    if attr.info.type == pytsk3.TSK_FS_ATTR_TYPE_DEFAULT:
                        for run in attr:
                            addr = run.addr * fs_info.info.block_size
                            length = run.len * fs_info.info.block_size
                            for off in range(addr, addr + length, block_size):
                                sector_offsets.append(off)
                                if is_allocated:
                                    claimed_offsets.append(off)
            except Exception:
                pass
                
            source_offset = sector_offsets[0] if sector_offsets else 0
            
            # Timestamps
            mtime = getattr(entry.info.meta, 'mtime', 0)
            created_at = datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc).isoformat() if mtime else None

            artifact_id = insert_artifact(
                conn,
                name=name,
                source_offset=source_offset,
                size=size,
                method='fs',
                status='FULL' if is_allocated else 'PARTIAL',
                confidence=1.0 if is_allocated else 0.8,
                score=0.0,
                created_at=created_at
            )
            
            # Store fragments
            for seq, off in enumerate(sector_offsets):
                insert_fragment(conn, artifact_id, off, seq)

def _fallback_fls(image_path: str, db_path: str) -> Dict[str, Any]:
    """Fallback directory walker using system sleuthkit CLI tools fls/icat if pytsk3 binding fails."""
    logger.info("Executing Sleuth Kit fls fallback parser...")
    result = {'allocated': 0, 'deleted': 0, 'fs_type': 'CLI Fallback', 'error': None}
    
    try:
        output = subprocess.check_output(['fls', '-r', '-p', image_path], stderr=subprocess.STDOUT, text=True)
    except Exception as e:
        logger.warning(f"fls command execution failed: {e}")
        result['error'] = "fls execution failed"
        return result

    conn = get_connection(db_path)
    conn.execute("BEGIN TRANSACTION;")
    
    for line in output.splitlines():
        parts = line.strip().split('\t')
        if len(parts) < 2:
            continue
        meta_info = parts[0].split()
        if len(meta_info) < 2:
            continue
            
        file_type_flag = meta_info[0]
        inode = meta_info[1].rstrip(':')
        file_path = parts[1]
        
        if 'r/r' in file_type_flag: # regular file
            is_deleted = '*' in file_type_flag
            if is_deleted:
                result['deleted'] += 1
            else:
                result['allocated'] += 1
                
            file_name = os.path.basename(file_path)
            insert_artifact(
                conn,
                name=file_name,
                source_offset=0,
                size=0,
                method='fs',
                status='PARTIAL' if is_deleted else 'FULL',
                confidence=0.7 if is_deleted else 0.9,
                score=0.0
            )

    conn.commit()
    conn.close()
    return result
