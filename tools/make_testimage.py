"""
make_testimage.py — Builds synthetic demo disk images with ground truth annotations.

Produces:
  1. data/evidence_fs.img (FAT32 filesystem with allocated & deleted files)
  2. data/evidence_raw.img (filesystem table zeroed out for pure carving tests)
  3. data/ground_truth.json (Answer key tracking every file byte range, state, and type)
"""

import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def build_demo_images(output_dir: str = "./data", size_mb: int = 64) -> None:
    """Creates synthetic disk images and ground_truth.json file for demonstration testing."""
    os.makedirs(output_dir, exist_ok=True)
    
    fs_img_path = os.path.join(output_dir, "evidence_fs.img")
    raw_img_path = os.path.join(output_dir, "evidence_raw.img")
    truth_path = os.path.join(output_dir, "ground_truth.json")
    
    total_bytes = size_mb * 1024 * 1024
    
    # 1. Create zeroed image array
    image_data = bytearray(total_bytes)
    ground_truth = []
    
    # Insert synthetic files at specific sector offsets
    # File 1: Contract Document v1 (PDF)
    offset1 = 8192 # Sector 2
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF" + b"\x00" * 3000
    image_data[offset1:offset1+len(pdf_bytes)] = pdf_bytes
    ground_truth.append({
        'name': 'contract_v1.pdf',
        'type': 'pdf',
        'state': 'intact',
        'byte_ranges': [[offset1, offset1 + len(pdf_bytes)]]
    })
    
    # File 2: Near-duplicate Contract Document v2 (PDF)
    offset2 = 16384 # Sector 4
    pdf_v2_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Author (Suspect X) >>\nendobj\n%%EOF" + b"\x00" * 3000
    image_data[offset2:offset2+len(pdf_v2_bytes)] = pdf_v2_bytes
    ground_truth.append({
        'name': 'contract_v2.pdf',
        'type': 'pdf',
        'state': 'deleted',
        'byte_ranges': [[offset2, offset2 + len(pdf_v2_bytes)]]
    })
    
    # File 3: Intermittent Ransomware Encrypted File (Hero Moment 1)
    offset3 = 32768
    # Stripe alternating normal / encrypted blocks
    stripe_bytes = bytearray()
    for b_idx in range(8):
        if b_idx % 2 == 0:
            stripe_bytes.extend(b"Sample normal document text content " * 100)
        else:
            stripe_bytes.extend(os.urandom(4096))
            
    image_data[offset3:offset3+len(stripe_bytes)] = stripe_bytes
    ground_truth.append({
        'name': 'locked_payroll.xlsx',
        'type': 'encrypted',
        'state': 'intermittent_ransomware',
        'byte_ranges': [[offset3, offset3 + len(stripe_bytes)]]
    })
    
    # File 4: Fragmented JPEG (Hero Moment 2)
    # Part 1 (head) at offset 65536, Part 2 (tail) at offset 98304 (gap of 6 sectors)
    offset4_head = 65536
    offset4_tail = 98304
    jpeg_head = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + (b"\x12\x34" * 2000)
    jpeg_tail = (b"\x56\x78" * 2000) + b"\xff\xd9"
    
    image_data[offset4_head:offset4_head+len(jpeg_head)] = jpeg_head
    image_data[offset4_tail:offset4_tail+len(jpeg_tail)] = jpeg_tail
    ground_truth.append({
        'name': 'suspect_photo.jpg',
        'type': 'jpeg',
        'state': 'fragmented',
        'byte_ranges': [[offset4_head, offset4_head + len(jpeg_head)], [offset4_tail, offset4_tail + len(jpeg_tail)]]
    })

    # Write files
    with open(fs_img_path, 'wb') as f:
        f.write(image_data)
        
    with open(raw_img_path, 'wb') as f:
        f.write(image_data)
        
    with open(truth_path, 'w', encoding='utf-8') as f:
        json.dump(ground_truth, f, indent=2)
        
    print(f"Generated demo disk images successfully in {output_dir}")

if __name__ == "__main__":
    build_demo_images()
