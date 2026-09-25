// Mock forensic dataset. Deterministic so SSR and client render identically.

export type BlockType =
  | "JPEG"
  | "PDF"
  | "ZIP"
  | "EXE"
  | "TEXT"
  | "ENCRYPTED"
  | "ZERO";

export const BLOCK_TYPES: BlockType[] = [
  "JPEG",
  "PDF",
  "ZIP",
  "EXE",
  "TEXT",
  "ENCRYPTED",
  "ZERO",
];

export const BLOCK_COLOR: Record<BlockType, string> = {
  JPEG: "var(--color-intact)",
  PDF: "var(--color-violet-evidence)",
  ZIP: "var(--color-document)",
  EXE: "var(--color-primary)",
  TEXT: "var(--color-text-evidence)",
  ENCRYPTED: "var(--color-encrypted)",
  ZERO: "var(--color-unalloc)",
};

export interface DiskBlock {
  index: number;
  type: BlockType;
  entropy: number;
  confidence: number;
  chiSquare: number;
}

// Small deterministic PRNG (mulberry32)
function rng(seed: number) {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export const TOTAL_BLOCKS = 16384;
export const BLOCK_SIZE = 4096;

function buildBlocks(): DiskBlock[] {
  const rand = rng(20260925);
  const blocks: DiskBlock[] = [];
  let i = 0;
  while (i < TOTAL_BLOCKS) {
    const roll = rand();
    let type: BlockType;
    if (roll < 0.34) type = "ZERO";
    else if (roll < 0.52) type = "JPEG";
    else if (roll < 0.65) type = "PDF";
    else if (roll < 0.74) type = "ZIP";
    else if (roll < 0.81) type = "EXE";
    else if (roll < 0.91) type = "TEXT";
    else type = "ENCRYPTED";

    const run = 1 + Math.floor(rand() * 24);
    for (let k = 0; k < run && i < TOTAL_BLOCKS; k++, i++) {
      const base =
        type === "ZERO"
          ? 0.05
          : type === "TEXT"
            ? 4.4
            : type === "PDF"
              ? 6.1
              : type === "EXE"
                ? 6.5
                : type === "JPEG"
                  ? 7.3
                  : type === "ZIP"
                    ? 7.6
                    : 7.95;
      blocks.push({
        index: i,
        type,
        entropy: Math.max(0, Math.min(8, base + (rand() - 0.5) * 0.5)),
        confidence: 0.62 + rand() * 0.37,
        chiSquare: Math.round((type === "ENCRYPTED" ? 240 : 1200) * (0.6 + rand())),
      });
    }
  }
  return blocks;
}

export const DISK_BLOCKS = buildBlocks();

export function hex(n: number, width = 8) {
  return "0x" + n.toString(16).toUpperCase().padStart(width, "0");
}

export function hexDump(blockIndex: number, rows = 16) {
  const rand = rng(blockIndex * 7919 + 13);
  const out: { offset: string; bytes: string[]; ascii: string }[] = [];
  const block = DISK_BLOCKS[blockIndex];
  for (let r = 0; r < rows; r++) {
    const bytes: string[] = [];
    let ascii = "";
    for (let c = 0; c < 16; c++) {
      let v: number;
      if (block?.type === "ZERO") v = 0;
      else if (block?.type === "TEXT") v = 32 + Math.floor(rand() * 94);
      else v = Math.floor(rand() * 256);
      bytes.push(v.toString(16).toUpperCase().padStart(2, "0"));
      ascii += v >= 32 && v <= 126 ? String.fromCharCode(v) : ".";
    }
    out.push({
      offset: hex(blockIndex * BLOCK_SIZE + r * 16),
      bytes,
      ascii,
    });
  }
  return out;
}

export interface Artifact {
  id: string;
  name: string;
  offset: number;
  type: "JPEG" | "PDF" | "DOCX" | "TXT" | "PNG" | "XLSX" | "EXE";
  status: "FULL" | "PARTIAL" | "ENCRYPTED" | "FRAGMENT";
  completeness: number;
  priority: number;
  method: "FS Metadata" | "Carved" | "Reassembled";
  sizeKb: number;
  sha256: string;
  tlsh: string;
  entropyStrip: number[];
  validation: { label: string; value: string; ok: boolean }[];
  textPreview: string;
}

function sha(seed: number) {
  const rand = rng(seed);
  let s = "";
  for (let i = 0; i < 64; i++) s += "0123456789abcdef"[Math.floor(rand() * 16)];
  return s;
}

const NAMES = [
  "recovered_photo_B14.jpg",
  "contract_draft_v3.pdf",
  "contract_draft_v2.pdf",
  "contract_final.pdf",
  "site_photo_0421.jpg",
  "site_photo_0422.jpg",
  "payroll_q3.xlsx",
  "ledger_backup.xlsx",
  "id_scan_front.png",
  "id_scan_back.png",
  "notes_interview.txt",
  "wallet_export.txt",
  "deploy_agent.exe",
  "memo_internal.docx",
  "ndas_signed.pdf",
  "cctv_still_23.jpg",
  "invoice_8821.pdf",
  "keylog_dump.txt",
  "backup_manifest.txt",
  "server_config.docx",
  "crypto_keys.txt",
  "recovered_frag_0x1A40.jpg",
  "recovered_frag_0x2C80.pdf",
  "archive_partial.zip.docx",
  "email_thread.txt",
  ...Array.from({ length: 17 }, (_, i) => `recovered_evidence_${String(i + 25).padStart(2, "0")}.${["pdf", "jpg", "txt", "docx"][i % 4]}`),
];

const TEXTS = [
  "CONFIDENTIAL — SERVICE AGREEMENT between Northline Holdings and Arcadia Systems. Payment terms net-30. Contact: m.okafor@northline-hold.com",
  "Interview notes 09/22: subject referenced an off-book transfer to wallet 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa on the evening of the 18th.",
  "Payroll export Q3 — 214 records. Contains SSN-like patterns and card number 4539 1488 0343 6467 (Luhn valid).",
  "Internal memo: staging credentials rotated. Do not distribute outside the incident channel.",
];

function buildArtifacts(): Artifact[] {
  const rand = rng(424242);
  return NAMES.map((name, i) => {
    const ext = (name.split(".").pop() ?? "TXT").toUpperCase();
    const type = (
      ["JPG", "JPEG"].includes(ext)
        ? "JPEG"
        : ext === "PDF"
          ? "PDF"
          : ext === "PNG"
            ? "PNG"
            : ext === "XLSX"
              ? "XLSX"
              : ext === "DOCX"
                ? "DOCX"
                : ext === "EXE"
                  ? "EXE"
                  : "TXT"
    ) as Artifact["type"];
    const roll = rand();
    const status: Artifact["status"] =
      roll < 0.5 ? "FULL" : roll < 0.72 ? "PARTIAL" : roll < 0.88 ? "ENCRYPTED" : "FRAGMENT";
    const completeness =
      status === "FULL" ? 100 : status === "PARTIAL" ? 45 + Math.floor(rand() * 45) : Math.floor(rand() * 40);
    const strip = Array.from({ length: 28 }, (_, k) =>
      status === "ENCRYPTED"
        ? k % 3 === 0
          ? 3 + rand() * 1.5
          : 7.6 + rand() * 0.4
        : 3 + rand() * 4,
    );
    return {
      id: `ART-${String(i + 1).padStart(4, "0")}`,
      name,
      offset: Math.floor(rand() * TOTAL_BLOCKS) * BLOCK_SIZE,
      type,
      status,
      completeness,
      priority:
        status === "ENCRYPTED"
          ? 70 + Math.floor(rand() * 30)
          : 20 + Math.floor(rand() * 75),
      method: roll < 0.4 ? "FS Metadata" : roll < 0.8 ? "Carved" : "Reassembled",
      sizeKb: 12 + Math.floor(rand() * 4800),
      sha256: sha(i + 1),
      tlsh: "T1" + sha(i + 99).slice(0, 34).toUpperCase(),
      entropyStrip: strip,
      validation: [
        {
          label: "Pillow MCU row decode",
          value: `${Math.floor(completeness * 4.8)} / 480 rows`,
          ok: completeness > 80,
        },
        {
          label: "PyPDF xref table",
          value: completeness > 60 ? "RESOLVED" : "BROKEN OFFSET",
          ok: completeness > 60,
        },
        {
          label: "CRC32 checksum",
          value: completeness === 100 ? "MATCH" : "MISMATCH",
          ok: completeness === 100,
        },
      ],
       textPreview: TEXTS[i % TEXTS.length] ?? "",
    };
  });
}

export const ARTIFACTS = buildArtifacts();

export const CASE = {
  id: "CASE-2026-ALPHA",
  imageName: "evidence_raw.img",
  imageSizeMb: 64,
  sha256: "9f2c4b7ae1d83c05f6b9142ad7e0cb3358fa19e7c4d2b6801af53e9c27d6b4aa",
  acquired: "2026-09-25T04:12:08Z",
  examiner: "J. Bhuvanesh",
  clearance: "Senior Forensics Examiner",
  sessionId: "SESS-7A21-FF09",
  engineMs: 8420,
};

export const KPIS = {
  scannedBlocks: TOTAL_BLOCKS,
  recovered: ARTIFACTS.length,
  intactRate: Math.round(
    (ARTIFACTS.filter((a) => a.status === "FULL").length / ARTIFACTS.length) * 100,
  ),
  ransomwareSignatures: ARTIFACTS.filter((a) => a.status === "ENCRYPTED").length,
};

export const BENCHMARKS = [
  {
    metric: "Corrupt / junk file dump",
    evidra: 4,
    photorec: 40,
    note: "10× cleaner output",
    lowerIsBetter: true,
  },
  {
    metric: "Fragmented file reassembly",
    evidra: 80,
    photorec: 0,
    note: "New capability",
    lowerIsBetter: false,
  },
  {
    metric: "Ransomware signature detection",
    evidra: 92,
    photorec: 0,
    note: "Visible attack pattern",
    lowerIsBetter: false,
  },
];

export interface GraphNode {
  id: string;
  label: string;
  kind: "file" | "fragment";
  status: Artifact["status"];
  x: number;
  y: number;
  cluster: number;
}
export interface GraphEdge {
  source: string;
  target: string;
  kind: "duplicate" | "near-duplicate" | "reassembly";
  weight: number;
}

function buildGraph() {
  const rand = rng(90210);
  const nodes: GraphNode[] = ARTIFACTS.slice(0, 18).map((a, i) => {
    const cluster = i % 4;
    const angle = (i / 18) * Math.PI * 2;
    const cx = [26, 72, 30, 74][cluster] ?? 50;
    const cy = [28, 26, 74, 72][cluster] ?? 50;
    return {
      id: a.id,
      label: a.name,
      kind: a.status === "FRAGMENT" ? "fragment" : "file",
      status: a.status,
      x: cx + Math.cos(angle) * (8 + rand() * 9),
      y: cy + Math.sin(angle) * (8 + rand() * 9),
      cluster,
    };
  });
  const edges: GraphEdge[] = [];
  for (let c = 0; c < 4; c++) {
    const group = nodes.filter((n) => n.cluster === c);
    for (let i = 1; i < group.length; i++) {
      const r = rand();
      edges.push({
        source: group[0]!.id,
        target: group[i]!.id,
        kind: r < 0.25 ? "duplicate" : r < 0.7 ? "near-duplicate" : "reassembly",
        weight: Math.round(72 + rand() * 27),
      });
    }
  }
  return { nodes, edges };
}

export const GRAPH = buildGraph();

export const REVISION_TIMELINE = [
  { at: "2026-08-02 09:14", label: "contract_draft_v2.pdf", note: "TLSH 94% similar" },
  { at: "2026-08-09 16:41", label: "contract_draft_v3.pdf", note: "TLSH 97% similar" },
  { at: "2026-08-14 11:02", label: "contract_final.pdf", note: "Signed revision" },
];

export const CUSTODY_LOG = [
  { at: "04:12:08Z", actor: "J. Bhuvanesh", action: "Image mounted read-only (MMAP)", hash: "9f2c4b7a" },
  { at: "04:12:11Z", actor: "ENGINE", action: "Pre-analysis SHA-256 computed", hash: "9f2c4b7a" },
  { at: "04:13:02Z", actor: "ENGINE", action: "16,384 blocks classified (LightGBM)", hash: "c71d0e42" },
  { at: "04:14:55Z", actor: "ENGINE", action: "42 artifacts carved & reassembled", hash: "ab30f519" },
  { at: "04:15:31Z", actor: "J. Bhuvanesh", action: "Cluster 0x0002E000 inspected", hash: "5fe1cc08" },
  { at: "04:18:44Z", actor: "ENGINE", action: "Post-analysis SHA-256 verified — unchanged", hash: "9f2c4b7a" },
];

export const PII_FINDINGS = [
  { kind: "Email", value: "m.okafor@northline-hold.com", source: "ART-0001" },
  { kind: "Credit card (Luhn valid)", value: "4539 14** **** 6467", source: "ART-0006" },
  { kind: "Crypto address", value: "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", source: "ART-0010" },
  { kind: "Person name", value: "M. Okafor", source: "ART-0003" },
];

export const AI_BRIEF =
  "Recovered evidence centres on a three-revision contract between Northline Holdings and Arcadia Systems, with interview notes referencing an off-book transfer to a Bitcoin address. Intermittent high-entropy striping across 6 artifacts matches a partial-encryption ransomware pattern rather than full-volume encryption.";
