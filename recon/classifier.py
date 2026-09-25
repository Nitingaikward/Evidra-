"""
classifier.py — LightGBM Block Type Classifier.

Classifies 4096-byte sector blocks into 9 target forensic classes:
['jpeg', 'png', 'pdf', 'zip_office', 'text_html', 'exe', 'compressed_other', 'encrypted_random', 'zero_empty']
"""

import os
import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
from collections import Counter
import lightgbm as lgb
from sklearn.metrics import classification_report, confusion_matrix

from recon.features import extract_features_batch, shannon_entropy, byte_histogram
from recon.db import get_connection, insert_block
from recon.ingest import iter_blocks, ImageHandle

logger = logging.getLogger(__name__)

CLASS_NAMES = [
    'jpeg',
    'png',
    'pdf',
    'zip_office',
    'text_html',
    'exe',
    'compressed_other',
    'encrypted_random',
    'zero_empty'
]

CLASS_TO_IDX = {name: i for i, name in enumerate(CLASS_NAMES)}
IDX_TO_CLASS = {i: name for i, name in enumerate(CLASS_NAMES)}

BLOCK_SIZE = 4096
DEFAULT_MODEL_PATH = './models/block_clf.txt'

def train(
    X: np.ndarray,
    y: np.ndarray,
    model_path: str = DEFAULT_MODEL_PATH,
    n_estimators: int = 300
) -> lgb.Booster:
    """
    Trains a LightGBM multiclass model on extracted block feature matrix X and integer label array y.
    Saves model parameters to model_path.
    """
    os.makedirs(os.path.dirname(os.path.abspath(model_path)), exist_ok=True)
    
    train_data = lgb.Dataset(X, label=y)
    
    params = {
        'objective': 'multiclass',
        'num_class': len(CLASS_NAMES),
        'metric': 'multi_logloss',
        'num_leaves': 63,
        'learning_rate': 0.05,
        'feature_fraction': 0.8,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'verbose': -1,
        'n_jobs': -1
    }
    
    logger.info(f"Training LightGBM model on {X.shape[0]} blocks...")
    booster = lgb.train(
        params,
        train_data,
        num_boost_round=n_estimators
    )
    
    booster.save_model(model_path)
    logger.info(f"Saved LightGBM model to {model_path}")
    return booster

def load(model_path: str = DEFAULT_MODEL_PATH) -> lgb.Booster:
    """Loads trained LightGBM model from disk file."""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Trained model file not found at {model_path}")
    return lgb.Booster(model_file=model_path)

def predict_proba(model: lgb.Booster, X: np.ndarray) -> np.ndarray:
    """Returns (N, 9) class probability matrix for input feature matrix X."""
    return model.predict(X)

def predict_classes(model: lgb.Booster, X: np.ndarray) -> List[str]:
    """Returns predicted class name string for each feature vector in X."""
    probs = predict_proba(model, X)
    idxs = np.argmax(probs, axis=1)
    return [IDX_TO_CLASS[i] for i in idxs]

def smooth_predictions(preds: List[str], window: int = 5) -> List[str]:
    """
    Applies sliding-window majority vote smoothing across adjacent disk sector predictions
    to eliminate isolated false-positive noise along contiguous file boundaries.
    """
    if len(preds) < window:
        return preds
    
    half_w = window // 2
    smoothed = list(preds)
    
    for i in range(len(preds)):
        start = max(0, i - half_w)
        end = min(len(preds), i + half_w + 1)
        sub = preds[start:end]
        # Most common class in window
        counts = Counter(sub)
        most_common = counts.most_common(1)[0][0]
        smoothed[i] = most_common
        
    return smoothed

def classify_image_blocks(
    model: lgb.Booster,
    handle: ImageHandle,
    db_path: str,
    batch_size: int = 512
) -> List[Tuple[int, str, float, float]]:
    """
    Iterates over all blocks in ImageHandle, extracts features, predicts class & confidence,
    applies spatial majority smoothing, and writes results into the case.db `blocks` table.
    
    Returns list of tuples: [(offset, class_pred, entropy, confidence), ...]
    """
    logger.info(f"Beginning ML block classification for {handle.path}...")
    
    offsets: List[int] = []
    block_bytes_list: List[bytes] = []
    entropies: List[float] = []
    
    # Collect blocks
    for offset, b_bytes in iter_blocks(handle):
        offsets.append(offset)
        block_bytes_list.append(b_bytes)
        hist = byte_histogram(b_bytes)
        entropies.append(shannon_entropy(hist))
        
    total_blocks = len(block_bytes_list)
    logger.info(f"Extracted block stream ({total_blocks} total 4KB blocks). Feature extraction starting...")
    
    raw_preds: List[str] = []
    confidences: List[float] = []
    
    # Process in batches
    for i in range(0, total_blocks, batch_size):
        batch = block_bytes_list[i:i + batch_size]
        X_batch = extract_features_batch(batch)
        probs = predict_proba(model, X_batch)
        
        for p in probs:
            best_idx = int(np.argmax(p))
            raw_preds.append(IDX_TO_CLASS[best_idx])
            confidences.append(float(p[best_idx]))
            
    # Apply spatial smoothing
    smoothed_preds = smooth_predictions(raw_preds, window=5)
    
    # Database insertion
    conn = get_connection(db_path)
    conn.execute("BEGIN TRANSACTION;")
    results = []
    
    for offset, cls_pred, ent, conf in zip(offsets, smoothed_preds, entropies, confidences):
        insert_block(conn, offset, cls_pred, ent, conf)
        results.append((offset, cls_pred, ent, conf))
        
    conn.commit()
    conn.close()
    logger.info(f"Classification finished. Stored {len(results)} block records in {db_path}.")
    
    return results

def confusion_report(y_true: List[str], y_pred: List[str]) -> str:
    """Generates formatted confusion matrix and per-class classification metrics report."""
    report = classification_report(y_true, y_pred, target_names=CLASS_NAMES, zero_division=0)
    matrix = confusion_matrix(y_true, y_pred, labels=CLASS_NAMES)
    
    output = "=== RECON Block Classifier Evaluation ===\n\n"
    output += report + "\n"
    output += "Confusion Matrix (Rows=True, Cols=Pred):\n"
    output += f"{'Class':<18} " + " ".join([f"{c[:5]:>6}" for c in CLASS_NAMES]) + "\n"
    for idx, row in enumerate(matrix):
        output += f"{CLASS_NAMES[idx]:<18} " + " ".join([f"{v:>6}" for v in row]) + "\n"
        
    return output
