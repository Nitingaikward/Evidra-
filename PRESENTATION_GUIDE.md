# 🎤 Evidra (RECON) — Slide-by-Slide Presentation & Pitch Guide

This guide breaks down every slide in **`Evidra_RECON_Hackathon_Pitch_5dbfa82e.pptx`**, providing:
- **Slide Objective & Key Visuals**
- **Exact Speaker Script (30–45s per slide)**
- **Technical Deep-Dive & Judge Q&A Defense**
- **The Forensic Boundary: Why LLM usage is strictly controlled**

---

## 📑 Slide-by-Slide Breakdown

---

### **Slide 1: Title & Team**
* **Header:** `EVIDRA (RECON) // DIGITAL FORENSICS // 24H BUILD`
* **Team Members:** Anusha A • J Bhuvanesh • Nitin S • Nandhitha S
* **Visuals:** Simulated raw hex offsets (`B00`, `H 0.18`, etc.) and entropy status indicators.
* **Tagline:** *"Bridging the gap between blind signature carvers and intelligent forensic reconstruction."*

#### 🎙️ Speaker Script:
> "Good morning, judges. We are Team Evidra—Anusha, Bhuvanesh, Nitin, and Nandhitha. Today, we present **Evidra (RECON)**, an AI-assisted digital forensics engine designed to reconstruct, validate, and prioritize evidence from damaged, formatted, or ransomware-attacked storage media where traditional filesystem metadata is completely lost."

---

### **Slide 2: Problem / The 3 Layers of Forensics**
* **Key Visual:** 3-layer stack comparison showing where traditional tools break down.
* **Punchline:** *"The recovery stack breaks exactly where evidence matters."*

#### 🎙️ Speaker Script:
> "In digital forensics, investigators work across three layers. 
> - **Layer 1** relies on filesystem metadata like Autopsy or Sleuth Kit. But if a suspect quick-formats or wipes the partition table, it recovers zero files.
> - **Layer 2** uses traditional signature carvers like PhotoRec. They blindly scan for header and footer magic bytes. But they assume every file is contiguous, fail on fragmented files, and flood investigators with thousands of corrupted, unusable files.
> - This leaves a massive **Layer 3 Forensic Void**—where deleted files, fragmented photos, and encrypted documents physically exist on disk, but are completely unusable. Evidra fills this void."

#### ❓ Anticipated Judge Q&A:
* **Q:** *Isn't PhotoRec already good enough for raw carving?*
* **A:** *PhotoRec dumps files without any integrity check or understanding of fragmentation. If a 1 MB photo is split into two non-contiguous chunks, PhotoRec gives you a half-gray, broken file. Evidra solves this.*

---

### **Slide 3: Solution / Evidra (RECON) Pipeline**
* **Key Visual:** 7-stage automated horizontal pipeline from read-only raw input to court-ready output.
* **Core Philosophy:** *"No black-box validity decisions. ML narrows the search; decoders prove the result."*

#### 🎙️ Speaker Script:
> "Evidra replaces blind carving with an end-to-end 7-stage pipeline. We ingest raw disk images read-only with cryptographic SHA-256 verification. We classify every 4KB block using machine learning, carve using AI boundary awareness, reassemble fragmented files with bounded gap search, deterministically validate format integrity, link related evidence via fuzzy hashing, and produce a prioritized, court-ready report."

---

### **Slide 4: Core Innovation 01 / 4KB Block-Level AI**
* **Key Visual:** 256-bin histogram, Shannon entropy ($H$), Chi-square ($\chi^2$), and byte-run feature extraction feeding a LightGBM model to generate an interactive disk heatmap.

#### 🎙️ Speaker Script:
> "Mid-file fragments don't have file headers—they just look like raw binary bytes. Evidra extracts a rich statistical feature vector from every single 4KB block: byte histograms, Shannon entropy, chi-square uniformity, and format markers. Our LightGBM model classifies blocks in milliseconds on CPU into types like JPEG, PDF, Executable, or Encrypted, lighting up an interactive disk heatmap of unallocated space."

---

### **Slide 5: Core Innovation 02 / Bifragment Gap Carving**
* **Key Visual:** Diagram showing broken carve at byte 28,672, candidate pruning by ML, and bounded gap search stitching Block A and Block B.

#### 🎙️ Speaker Script:
> "On real disks, files get fragmented across non-adjacent clusters. When standard carving hits a corrupt sector, it stops. Evidra turns decoder failure into a search coordinate. It prunes candidate continuation blocks using our ML classifier, tests bounded gap offsets, and uses Pillow MCU decoders to stitch the orphan pieces together—recovering full images where PhotoRec returns broken files."

---

### **Slide 6: Core Innovation 03 / Intermittent Ransomware Visualizer**
* **Key Visual:** Alternating high/low entropy bar chart showing the periodic 4KB attack pattern.

#### 🎙️ Speaker Script:
> "Modern ransomware uses intermittent encryption—encrypting only every second or third block to maximize speed and evade whole-file detection tripwires. Evidra computes a per-block entropy strip across recovered files. This instantly exposes the alternating high/low entropy cadence, giving investigators clear visual proof of a ransomware attack pattern."

---

### **Slide 7: Core Innovation 04 / Evidence Relationship Graph**
* **Key Visual:** NetworkX graph clustering `contract_v1.pdf`, `contract_v2.pdf`, `orphan_B143`, and `timeline_event`.

#### 🎙️ Speaker Script:
> "Traditional tools dump thousands of disconnected files into a folder. Evidra uses Locality-Sensitive Hashing (TLSH) and ssdeep fuzzy hashing to build an evidence relationship graph. It automatically clusters different draft revisions of suspect documents, links orphaned fragments back to parent files, and maps chronological timelines."

---

### **Slide 8: Forensic Hygiene & Court Admissibility**
* **Key Visual:** The Integrity Chain & the Strict Validity Boundary between Decoders and the LLM.
* **Core Rule:** *"Zero LLM hallucination in the evidence decision path."*

#### 🎙️ Speaker Script:
> "Forensic evidence must be legally admissible under standards like the Daubert standard. In Evidra, AI proposes and assists, but deterministic decoders and cryptographic hashes remain the absolute source of truth. We strictly limit the LLM to plain-English summarization and entity extraction—the LLM is never allowed to decide whether a file is valid or corrupt."

---

### **Slide 9: Benchmark vs. PhotoRec (Hard Numbers)**
* **Key Visual:** Benchmark cards showing 10× cleaner output ($<4\%$ junk vs $40\%$), $80\%$ fragment reassembly, and $>92\%$ ransomware detection.

#### 🎙️ Speaker Script:
> "We evaluated Evidra against PhotoRec on the exact same corrupted disk image with known ground truth. PhotoRec flooded the output with 40% corrupt junk; Evidra reduced false positives to under 4%. PhotoRec recovered 0% of fragmented files; Evidra reassembled 80%. And while PhotoRec completely missed ransomware encryption, Evidra flagged it with over 92% precision."

---

### **Slide 10: Vision & Live Demo**
* **Key Visual:** Architecture stack recap (Python 3.12, LightGBM, Magika, pytsk3, TLSH, Streamlit, SQLite) with the live demo transition.

#### 🎙️ Speaker Script:
> "Evidra transforms raw, corrupted bytes into prioritized, court-ready evidence in seconds. Let's switch over to the live dashboard and inspect the evidence."

---

# 🧠 The Forensic Boundary: Why LLM Usage is Strictly Limited

One of the most impressive technical aspects of Evidra is its **principled architecture regarding LLMs**. Here is why the LLM is restricted to triage and summarization:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 THE VALIDITY BOUNDARY                                  │
├───────────────────────────────────────────┬────────────────────────────────────────────┤
│ 🛡️ DETERMINISTIC ENGINES (Source of Truth) │ 🤖 LLM LAYER (Human Triage & Explanation)  │
├───────────────────────────────────────────┼────────────────────────────────────────────┤
│ • Pillow / libjpeg (Image decode checks)  │ • Summarizes 50 extracted email bodies     │
│ • pypdf (PDF xref & page validation)      │ • Extracts entities (names, dates, IBANs)  │
│ • zipfile / CRC32 (Archive verification)  │ • Drafts plain-language investigator notes │
│ • SHA-256 / TLSH (Cryptographic hashes)   │ • Synthesizes case timeline narratives     │
│ ❌ NEVER allows hallucinations             │ ⚠️ Strictly labeled as AI-generated text   │
└───────────────────────────────────────────┴────────────────────────────────────────────┘
```

### 1. ⚖️ Legal Standards & Court Admissibility (The Daubert Standard)
* In judicial proceedings, digital evidence must be **reproducible, mathematically verifiable, and auditable**.
* If an expert witness claims a file was valid because "an AI model said so," the evidence is susceptible to being thrown out as inadmissible.
* If the testimony states: *"The file passed strict RFC-compliant binary parsing with matching CRC32 checksums and a verifiable SHA-256 offset"*, it is **100% court-admissible**.

### 2. 🧩 LLMs Cannot Calculate Binary Bitstreams
* LLMs are probabilistic language token predictors—they cannot reliably compute CRC32 checksums, verify DEFLATE tables, or validate Huffman coding trees without hallucinating.
* Deterministic Python format decoders execute in **sub-millisecond CPU time**, have zero hallucination risk, and cost nothing.

### 3. ⚡ Computational Scalability
* A 64 MB disk image contains **16,384** 4KB blocks.
* Streaming raw binary hex to an LLM would exhaust token limits, introduce immense latency, and incur significant API costs.
* Our **LightGBM model** classifies all 16,384 blocks on a local CPU in **under 3 seconds**.

---

### 💡 The 1-Sentence Pitch to Judges on AI Safety:
> *"In forensics, machine learning narrows the search space and accelerates human review, but deterministic decoders and cryptographic hashes remain the immutable source of truth."*
