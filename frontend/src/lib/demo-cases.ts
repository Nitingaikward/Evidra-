export const DEMO_CASES = [
  { id: "CASE-2026-ALPHA", urgency: "Critical", title: "Wiped SSD / LockBit Intermittent Ransomware", image: "evidence_raw.img", size: "64 MB", recovered: "42 files recovered", integrity: "94% integrity", updated: "25 Sep 2026 · 04:18 UTC", tone: "encrypted" },
  { id: "CASE-2026-BETA", urgency: "In Review", title: "Formatted FAT32 Corporate Espionage", image: "evidence_fs.img", size: "128 MB", recovered: "89 files recovered", integrity: "Under review", updated: "23 Sep 2026 · 11:32 UTC", tone: "partial" },
  { id: "CASE-2026-GAMMA", urgency: "Archived", title: "Server Log & Document Reassembly", image: "server_dump.raw", size: "512 MB", recovered: "Archive complete", integrity: "Verified", updated: "18 Sep 2026 · 16:05 UTC", tone: "muted" },
] as const;
