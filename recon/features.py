"""
features.py — Vectorized per-block feature extraction for block type classification.

Extracts statistical, structural, and byte-frequency features from 4096-byte blocks
to distinguish between JPEGs, PDFs, text, compressed, encrypted, executable, and zero blocks.
"""

import math
import numpy as np
from typing import List, Dict, Tuple, Any

FEATURE_NAMES = [
    # 0..255: byte histogram bins (normalized)
    *[f"hist_{i}" for i in range(256)],
    "shannon_entropy",
    "chi_square_uniform",
    "bigram_entropy",
    "printable_ratio",
    "zero_ratio",
    "longest_run",
    "ascii_ratio",
    "serial_correlation",
    "monte_carlo_pi_error",
    "marker_ff_non_zero",
    "marker_newline",
    "marker_angle_bracket",
    "marker_slash",
    "marker_null_runs",
    "marker_pk_header"
]

FEATURE_DIM = len(FEATURE_NAMES) # 256 + 15 = 271

def byte_histogram(block: bytes) -> np.ndarray:
    """Computes a 256-bin normalized byte frequency histogram."""
    arr = np.frombuffer(block, dtype=np.uint8)
    counts = np.bincount(arr, minlength=256)
    return (counts / len(block)).astype(np.float32)

def shannon_entropy(hist: np.ndarray) -> float:
    """Computes Shannon entropy (0 to 8.0 bits per byte) from normalized histogram."""
    nonzero = hist[hist > 0]
    return float(-np.sum(nonzero * np.log2(nonzero)))

def chi_square_uniform(hist: np.ndarray, block_len: int = 4096) -> float:
    """Computes Chi-Square statistic testing deviation from a uniform byte distribution."""
    expected = block_len / 256.0
    observed = hist * block_len
    chi_sq = np.sum((observed - expected) ** 2 / expected)
    return float(chi_sq)

def bigram_entropy(block: bytes) -> float:
    """Computes normalized entropy of consecutive byte bigrams."""
    if len(block) < 2:
        return 0.0
    arr = np.frombuffer(block, dtype=np.uint8)
    bigrams = arr[:-1].astype(np.uint16) * 256 + arr[1:].astype(np.uint16)
    counts = np.bincount(bigrams, minlength=65536)
    probs = counts[counts > 0] / (len(block) - 1)
    return float(-np.sum(probs * np.log2(probs)) / 16.0)

def printable_ratio(block: bytes) -> float:
    """Fraction of printable ASCII characters (0x20 to 0x7E + newline/tab)."""
    arr = np.frombuffer(block, dtype=np.uint8)
    printable = np.isin(arr, [9, 10, 13] + list(range(32, 127)))
    return float(np.mean(printable))

def zero_ratio(block: bytes) -> float:
    """Fraction of null bytes (0x00)."""
    arr = np.frombuffer(block, dtype=np.uint8)
    return float(np.mean(arr == 0))

def longest_run(block: bytes) -> int:
    """Length of the longest consecutive identical-byte run."""
    if not block:
        return 0
    arr = np.frombuffer(block, dtype=np.uint8)
    if len(arr) == 0:
        return 0
    diffs = arr[1:] != arr[:-1]
    change_indices = np.where(diffs)[0] + 1
    run_lengths = np.diff(np.concatenate(([0], change_indices, [len(arr)])))
    return int(np.max(run_lengths))

def ascii_ratio(block: bytes) -> float:
    """Fraction of standard ASCII bytes (< 0x80)."""
    arr = np.frombuffer(block, dtype=np.uint8)
    return float(np.mean(arr < 128))

def serial_correlation(block: bytes) -> float:
    """Pearson correlation coefficient between consecutive bytes x[i] and x[i+1]."""
    if len(block) < 2:
        return 0.0
    arr = np.frombuffer(block, dtype=np.float64) # Use float64 to avoid overflow
    x = arr[:-1]
    y = arr[1:]
    var_x = np.var(x)
    var_y = np.var(y)
    if var_x == 0 or var_y == 0 or np.isnan(var_x) or np.isnan(var_y):
        return 0.0
    cov = np.mean((x - np.mean(x)) * (y - np.mean(y)))
    denom = np.sqrt(var_x * var_y)
    if denom == 0 or np.isnan(denom):
        return 0.0
    corr = cov / denom
    return float(0.0 if np.isnan(corr) else corr)

def monte_carlo_pi_error(block: bytes) -> float:
    """Estimates Pi using pairs of consecutive bytes as coordinates in a 256x256 unit square."""
    if len(block) < 4:
        return 1.0
    arr = np.frombuffer(block, dtype=np.uint8).astype(np.float32)
    x = arr[0::2]
    y = arr[1::2]
    min_len = min(len(x), len(y))
    if min_len == 0:
        return 1.0
    x = x[:min_len] / 255.0
    y = y[:min_len] / 255.0
    dist_sq = x*x + y*y
    inside = np.sum(dist_sq <= 1.0)
    pi_est = (inside / min_len) * 4.0
    return float(abs(pi_est - math.pi) / math.pi)

def format_markers(block: bytes) -> Dict[str, float]:
    """Counts key structural and magic byte markers."""
    arr = np.frombuffer(block, dtype=np.uint8)
    
    # JPEG marker stuffing: 0xFF followed by non-zero
    ff_mask = (arr[:-1] == 0xFF) & (arr[1:] != 0x00) & (arr[1:] != 0xFF)
    ff_count = float(np.sum(ff_mask))
    
    newline_count = float(np.sum(arr == 0x0A))
    angle_bracket_count = float(np.sum((arr == 0x3C) | (arr == 0x3E))) # < or >
    slash_count = float(np.sum((arr == 0x2F) | (arr == 0x5C))) # / or \
    
    # Null sequences (runs of 4+ zeros)
    null_seqs = 0.0
    if b'\x00\x00\x00\x00' in block:
        null_seqs = float(block.count(b'\x00\x00\x00\x00'))
        
    pk_header = 1.0 if block.startswith(b'PK\x03\x04') else 0.0
    
    return {
        "marker_ff_non_zero": ff_count,
        "marker_newline": newline_count,
        "marker_angle_bracket": angle_bracket_count,
        "marker_slash": slash_count,
        "marker_null_runs": null_seqs,
        "marker_pk_header": pk_header
    }

def extract_features(block: bytes) -> np.ndarray:
    """Extracts a 1D float32 feature vector of length FEATURE_DIM from a single block."""
    hist = byte_histogram(block)
    entropy = shannon_entropy(hist)
    chi_sq = chi_square_uniform(hist, len(block))
    bigram_ent = bigram_entropy(block)
    print_r = printable_ratio(block)
    z_r = zero_ratio(block)
    l_run = float(longest_run(block))
    asc_r = ascii_ratio(block)
    ser_corr = serial_correlation(block)
    pi_err = monte_carlo_pi_error(block)
    markers = format_markers(block)

    feats = np.empty(FEATURE_DIM, dtype=np.float32)
    feats[:256] = hist
    feats[256] = entropy
    feats[257] = chi_sq
    feats[258] = bigram_ent
    feats[259] = print_r
    feats[260] = z_r
    feats[261] = l_run
    feats[262] = asc_r
    feats[263] = ser_corr
    feats[264] = pi_err
    feats[265] = markers["marker_ff_non_zero"]
    feats[266] = markers["marker_newline"]
    feats[267] = markers["marker_angle_bracket"]
    feats[268] = markers["marker_slash"]
    feats[269] = markers["marker_null_runs"]
    feats[270] = markers["marker_pk_header"]

    return feats

def extract_features_batch(blocks: List[bytes]) -> np.ndarray:
    """Extracts feature vectors for a list of blocks in parallel/matrix layout."""
    matrix = np.zeros((len(blocks), FEATURE_DIM), dtype=np.float32)
    for i, b in enumerate(blocks):
        matrix[i] = extract_features(b)
    return matrix
