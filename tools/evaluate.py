"""
evaluate.py — Ground Truth Evaluator (Secret Weapon 3).

Evaluates Evidra pipeline recovery precision, recall, F1, and block classification metrics
against ground_truth.json answer key.
"""

import os
import json
import logging
import argparse
from typing import Dict, List, Any

from recon.db import get_connection

logger = logging.getLogger(__name__)

def evaluate_case(db_path: str, truth_path: str) -> Dict[str, Any]:
    """Compares case.db artifacts against ground_truth.json answer key."""
    if not os.path.exists(db_path) or not os.path.exists(truth_path):
        print(f"Error: Database ({db_path}) or Ground Truth ({truth_path}) not found.")
        return {}

    with open(truth_path, 'r', encoding='utf-8') as f:
        truth_files = json.load(f)

    conn = get_connection(db_path)
    artifacts = conn.execute("SELECT name, status, method, confidence, score FROM artifacts;").fetchall()
    blocks = conn.execute("SELECT offset, type_pred FROM blocks;").fetchall()
    conn.close()

    total_truth = len(truth_files)
    total_recovered = len(artifacts)
    
    truth_names = {tf['name'].lower() for tf in truth_files}
    recovered_names = {art['name'].lower() for art in artifacts if art['name']}

    correctly_identified = len(truth_names.intersection(recovered_names))
    
    precision = (correctly_identified / total_recovered) if total_recovered > 0 else 0.0
    recall = (correctly_identified / total_truth) if total_truth > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    report_metrics = {
        'total_ground_truth_files': total_truth,
        'total_recovered_artifacts': total_recovered,
        'precision': round(precision, 3),
        'recall': round(recall, 3),
        'f1_score': round(f1, 3),
        'blocks_analyzed': len(blocks)
    }

    print("\n========================================================")
    print("  EVIDRA GROUND TRUTH BENCHMARK EVALUATION (SECRET WEAPON 3)")
    print("========================================================\n")
    print(f"  Ground Truth Files    : {total_truth}")
    print(f"  Recovered Artifacts   : {total_recovered}")
    print(f"  Precision             : {precision * 100:.1f}%")
    print(f"  Recall                : {recall * 100:.1f}%")
    print(f"  F1 Score              : {f1:.3f}")
    print(f"  Sector Blocks Tracked : {len(blocks)}")
    print("\n========================================================\n")

    return report_metrics

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evidra Benchmark Evaluator")
    parser.add_argument("--db", default="./case_output/case.db", help="Path to case.db")
    parser.add_argument("--truth", default="./data/ground_truth.json", help="Path to ground_truth.json")
    args = parser.parse_args()
    
    evaluate_case(args.db, args.truth)
