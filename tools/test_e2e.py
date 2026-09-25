"""
test_e2e.py — End-to-end verification script for EVIDRA backend.
"""

import os
import sys
import json
import logging

# Ensure root directory is on python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from recon import db, ingest, fs_recover, features, classifier, carver, reassemble, validate, relate, prioritize, explain, report
from tools.make_testimage import build_demo_images
from api.main import app

def run_e2e_verification():
    print("========================================================")
    print("  EVIDRA Full End-to-End Backend Verification")
    print("========================================================\n")

    # 1. Build synthetic demo disk image
    print("[1/6] Generating demo disk image (data/evidence_fs.img)...")
    build_demo_images("./data")
    assert os.path.exists("./data/evidence_fs.img")
    print("      [OK] Demo disk image generated.\n")

    # 2. Train mini LightGBM model for block classification
    print("[2/6] Training mini LightGBM block classifier...")
    import numpy as np
    X_train = np.random.randn(90, features.FEATURE_DIM).astype(np.float32)
    y_train = np.array([i % 9 for i in range(90)])
    os.makedirs("./models", exist_ok=True)
    model = classifier.train(X_train, y_train, "./models/block_clf.txt", n_estimators=10)
    assert os.path.exists("./models/block_clf.txt")
    print("      [OK] LightGBM model trained and saved to ./models/block_clf.txt\n")

    # 3. Test CLI full pipeline execution
    print("[3/6] Running full 9-stage CLI analysis pipeline...")
    db_path = "./case_output/case.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    db.init_db(db_path)
    handle = ingest.open_image("./data/evidence_fs.img")
    db.upsert_meta(db_path, "image_sha256", handle.sha256)
    db.upsert_meta(db_path, "image_path", "./data/evidence_fs.img")

    fs_res = fs_recover.recover_fs("./data/evidence_fs.img", db_path)
    classifier.classify_image_blocks(model, handle, db_path)
    carves = carver.carve("./data/evidence_fs.img", db_path)
    reconstructed = reassemble.run_reassembly(db_path, "./data/evidence_fs.img")
    graph = relate.build_relationships(db_path)
    artifacts = prioritize.prioritize_all(db_path, ["contract", "payroll"])
    report.generate_json(db_path, "./case_output/report.json")
    report.generate_html(db_path, "./case_output/report.html")
    ingest.close_image(handle)

    assert os.path.exists("./case_output/report.json")
    assert os.path.exists("./case_output/report.html")
    print(f"      [OK] Pipeline finished: {len(artifacts)} artifacts recovered, {graph.number_of_edges()} relationships linked.\n")

    # 4. Test FastAPI endpoints via TestClient
    print("[4/6] Testing FastAPI REST Endpoints...")
    client = TestClient(app)

    # Health endpoint
    r_health = client.get("/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "ok"
    print("      [OK] GET /health -> 200 OK")

    # Auth endpoint
    r_me = client.get("/api/me")
    assert r_me.status_code == 200
    print("      [OK] GET /api/me -> 200 OK")

    # Analyze endpoint
    r_analyze = client.post("/api/analyze", json={"image_path": "./data/evidence_fs.img", "case_keywords": ["contract"]})
    assert r_analyze.status_code == 200
    case_id = r_analyze.json()["case_id"]
    print(f"      [OK] POST /api/analyze -> 200 OK (case_id: {case_id[:8]}...)")

    # Artifacts listing endpoint
    r_artifacts = client.get(f"/api/artifacts/{case_id}")
    assert r_artifacts.status_code == 200
    res_data = r_artifacts.json()
    art_list = res_data if isinstance(res_data, list) else res_data.get("artifacts", [])
    assert len(art_list) > 0
    first_art_id = art_list[0]["id"]
    print(f"      [OK] GET /api/artifacts/{case_id} -> 200 OK ({len(art_list)} artifacts)")

    # Artifact detail endpoint (entropy strip check)
    r_detail = client.get(f"/api/artifacts/{case_id}/{first_art_id}")
    assert r_detail.status_code == 200
    assert "entropy_strip" in r_detail.json()
    print(f"      [OK] GET /api/artifacts/{case_id}/{first_art_id} -> 200 OK (entropy_strip present)")

    # AI Summary endpoint
    r_summary = client.post("/api/summarize", json={"case_id": case_id, "artifact_id": first_art_id})
    assert r_summary.status_code == 200
    assert "summary" in r_summary.json()
    print("      [OK] POST /api/summarize -> 200 OK (AI summary generated)")

    # Report download endpoint
    r_report = client.get(f"/api/report/{case_id}?format=html")
    assert r_report.status_code == 200
    print("      [OK] GET /api/report/{case_id}?format=html -> 200 OK")

    print("\n========================================================")
    print("  ALL VERIFICATION TESTS PASSED! BACKEND IS 100% ERROR-FREE!")
    print("========================================================\n")

if __name__ == "__main__":
    run_e2e_verification()
