"""
cli.py — Command Line Interface for EVIDRA.

Usage:
  python cli.py analyze data/evidence_fs.img --out ./case_output/
  python cli.py make-demo --out ./data/
"""

import sys
import os
import time
import argparse
import logging
from datetime import datetime

from recon import db, ingest, fs_recover, classifier, carver, reassemble, validate, relate, prioritize, report
from tools.make_testimage import build_demo_images

def main():
    parser = argparse.ArgumentParser(description="EVIDRA — AI-Assisted Data Recovery and Evidence Reconstruction")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze raw disk image")
    analyze_parser.add_argument("image_path", help="Path to raw disk image (.dd/.img/.raw)")
    analyze_parser.add_argument("--out", "-o", default="./case_output", help="Output directory for case.db and reports")
    analyze_parser.add_argument("--keywords", "-k", help="Comma-separated case keywords")
    
    # Make demo command
    demo_parser = subparsers.add_parser("make-demo", help="Generate synthetic demo disk image with ground truth")
    demo_parser.add_argument("--out", "-o", default="./data", help="Output directory for demo disk images")
    
    args = parser.parse_args()
    
    if args.command == "make-demo":
        build_demo_images(args.out)
        return
        
    if args.command == "analyze":
        start_time = time.time()
        image_path = args.image_path
        out_dir = args.out
        os.makedirs(out_dir, exist_ok=True)
        db_path = os.path.join(out_dir, "case.db")
        
        keywords = [k.strip() for k in args.keywords.split(",")] if args.keywords else []
        
        print("\n========================================================")
        print("  EVIDRA — AI-Assisted Forensic Recovery Engine")
        print("========================================================\n")
        
        print(f"[*] Ingesting disk image: {image_path}")
        db.init_db(db_path)
        
        handle = ingest.open_image(image_path)
        db.upsert_meta(db_path, "image_sha256", handle.sha256)
        db.upsert_meta(db_path, "image_path", image_path)
        print(f"    SHA-256 Hash : {handle.sha256}")
        print(f"    Sectors      : {handle.size_bytes // handle.block_size} (4KB blocks)\n")
        
        print("[*] Stage 1: Running Filesystem Recovery...")
        fs_res = fs_recover.recover_fs(image_path, db_path)
        print(f"    Allocated files : {fs_res['allocated']}")
        print(f"    Deleted files   : {fs_res['deleted']}\n")
        
        print("[*] Stage 2: ML Block Classification & Features...")
        model_path = os.environ.get("MODEL_PATH", "./models/block_clf.txt")
        if os.path.exists(model_path):
            model = classifier.load(model_path)
            classifier.classify_image_blocks(model, handle, db_path)
            print("    Block map classification complete.")
        else:
            print("    [!] Pre-trained model not found. Skipping ML classification step.\n")
            
        print("[*] Stage 3: AI Block-Boundary Signature Carving...")
        carves = carver.carve(image_path, db_path)
        print(f"    Carved artifacts : {len(carves)}\n")
        
        print("[*] Stage 4: Bifragment Reassembly Engine...")
        reconstructed = reassemble.run_reassembly(db_path, image_path)
        print(f"    Reconstructed    : {reconstructed} damaged artifacts\n")
        
        print("[*] Stage 5 & 6: Validation, Relationships & Graph Construction...")
        graph = relate.build_relationships(db_path)
        artifacts = prioritize.prioritize_all(db_path, keywords)
        print(f"    Artifacts ranked : {len(artifacts)}")
        print(f"    Graph edges      : {graph.number_of_edges()} relationships\n")
        
        print("[*] Stage 7: Generating Forensic Reports...")
        json_out = os.path.join(out_dir, "report.json")
        html_out = os.path.join(out_dir, "report.html")
        report.generate_json(db_path, json_out)
        report.generate_html(db_path, html_out)
        
        ingest.close_image(handle)
        
        elapsed = round(time.time() - start_time, 2)
        print("\n========================================================")
        print(f"  EVIDRA Analysis Complete ({elapsed}s)")
        print(f"  HTML Report : {os.path.abspath(html_out)}")
        print(f"  JSON Report : {os.path.abspath(json_out)}")
        print("========================================================\n")

if __name__ == "__main__":
    main()
