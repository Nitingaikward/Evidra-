"""
ingest.py — Read-only image ingest, SHA-256 calculation, and block streaming.

Guarantees forensic integrity by:
1. Opening image read-only using mmap.
2. Calculating SHA-256 hash before and after processing.
3. Providing memory-efficient block-by-block streaming.
"""

import os
import mmap
import hashlib
import logging
from typing import Iterator, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class ImageHandle:
    path: str
    size_bytes: int
    sha256: str
    block_size: int
    mmap_obj: mmap.mmap
    file_obj: object

    def close(self):
        """Safely closes mmap and underlying file handle."""
        if self.mmap_obj:
            try:
                self.mmap_obj.close()
            except Exception as e:
                logger.warning(f"Error closing mmap: {e}")
        if self.file_obj:
            try:
                self.file_obj.close()
            except Exception as e:
                logger.warning(f"Error closing file object: {e}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

def calculate_sha256(path: str, chunk_size: int = 65536) -> str:
    """Computes SHA-256 checksum of a raw disk image file."""
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()

def open_image(path: str, block_size: int = 4096) -> ImageHandle:
    """
    Opens a disk image file read-only using mmap and computes initial SHA-256 hash.
    Raises FileNotFoundError or PermissionError if opening fails.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Disk image file not found: {path}")

    size_bytes = os.path.getsize(path)
    if size_bytes == 0:
        raise ValueError(f"Disk image file is empty: {path}")

    logger.info(f"Opening forensic image read-only: {path} ({size_bytes} bytes)")
    sha256_hash = calculate_sha256(path)
    logger.info(f"SHA-256 pre-analysis hash: {sha256_hash}")

    # Open read-only
    file_obj = open(path, 'rb')
    try:
        # Windows mmap read-only access
        mmap_obj = mmap.mmap(file_obj.fileno(), 0, access=mmap.ACCESS_READ)
    except Exception as e:
        file_obj.close()
        raise IOError(f"Failed to memory-map file {path}: {e}")

    return ImageHandle(
        path=path,
        size_bytes=size_bytes,
        sha256=sha256_hash,
        block_size=block_size,
        mmap_obj=mmap_obj,
        file_obj=file_obj
    )

def iter_blocks(handle: ImageHandle) -> Iterator[Tuple[int, bytes]]:
    """
    Iterates over the disk image in block_size chunks.
    Yields (byte_offset, block_bytes) for every block.
    """
    offset = 0
    total_bytes = handle.size_bytes
    block_size = handle.block_size
    mmap_obj = handle.mmap_obj

    while offset < total_bytes:
        length = min(block_size, total_bytes - offset)
        block = mmap_obj[offset:offset + length]
        # Pad last block if smaller than block_size
        if len(block) < block_size:
            block = block + b'\x00' * (block_size - len(block))
        yield offset, block
        offset += block_size

def close_image(handle: ImageHandle) -> str:
    """Closes image handle and verifies post-analysis SHA-256 checksum."""
    post_sha256 = calculate_sha256(handle.path)
    if post_sha256 != handle.sha256:
        logger.critical(f"FORENSIC INTEGRITY COMPROMISED! Hash mismatch for {handle.path}")
        logger.critical(f"Pre:  {handle.sha256}")
        logger.critical(f"Post: {post_sha256}")
    else:
        logger.info(f"Forensic integrity verified. SHA-256 unchanged: {post_sha256}")
    
    handle.close()
    return post_sha256
