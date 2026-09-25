import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Shell } from "@/components/Shell";
import { Badge, Btn, Panel, statusTone } from "@/components/ui/primitives";
import { useArtifacts } from "@/lib/api";
import { hex, type Artifact } from "@/lib/forensic-data";
import reconstructedEvidence from "@/assets/reconstructed-evidence.jpg";
import { Button } from "@/components/ui/button";
import { X, GitCompareArrows } from "lucide-react";

export const Route = createFileRoute("/artifacts")({
  head: () => ({
    meta: [
      { title: "Recovered Artifacts Triage — Evidra RECON" },
      {
        name: "description",
        content:
          "Triage recovered files by priority score, recovery method and integrity status, with per-block entropy and decoder validation logs.",
      },
      { property: "og:title", content: "Recovered Artifacts Triage — Evidra RECON" },
      {
        property: "og:description",
        content: "Sort, filter and inspect carved and reassembled evidence artifacts.",
      },
      { property: "og:type", content: "website" }, { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Artifacts,
});

const STATUSES = ["FULL", "PARTIAL", "ENCRYPTED", "FRAGMENT"] as const;

function Artifacts() {
  const { data: artifacts } = useArtifacts();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<string>("ALL");
  const [type, setType] = useState<string>("ALL");
  const [minScore, setMinScore] = useState(0);
  const [sortDesc, setSortDesc] = useState(true);
  const [selected, setSelected] = useState<Artifact | null>(null);
  const [compare, setCompare] = useState(false);
  const [after, setAfter] = useState(true);

  const types = useMemo(
    () => Array.from(new Set(artifacts?.map((a) => a.type) ?? [])),
    [artifacts],
  );

  const rows = useMemo(() => {
    const list = (artifacts ?? []).filter(
      (a) =>
        (status === "ALL" || a.status === status) &&
        (type === "ALL" || a.type === type) &&
        a.priority >= minScore &&
        a.name.toLowerCase().includes(q.toLowerCase()),
    );
    return list.sort((a, b) => (sortDesc ? b.priority - a.priority : a.priority - b.priority));
  }, [artifacts, status, type, minScore, q, sortDesc]);

  return (
    <Shell title="Evidence Explorer">
      <Panel
        title={`Artifact triage · ${rows.length} of ${artifacts?.length ?? 0}`}
        right={
          <Btn onClick={() => setSortDesc((s) => !s)}>
            Priority {sortDesc ? "↓" : "↑"}
          </Btn>
        }
      >
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="search filename…"
            className="w-56 rounded-sm border border-border bg-background px-3 py-1.5 font-mono text-[12px] outline-none placeholder:text-muted-foreground focus:border-primary/60"
          />
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="rounded-sm border border-border bg-background px-2 py-1.5 font-mono text-[11px] uppercase"
          >
            <option value="ALL">All statuses</option>
            {STATUSES.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
          <select
            value={type}
            onChange={(e) => setType(e.target.value)}
            className="rounded-sm border border-border bg-background px-2 py-1.5 font-mono text-[11px] uppercase"
          >
            <option value="ALL">All types</option>
            {types.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
          <label className="flex items-center gap-2 font-mono text-[11px] text-muted-foreground">
            MIN PRIORITY {minScore}
            <input
              type="range"
              min={0}
              max={100}
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
              className="accent-[var(--color-primary)]"
            />
          </label>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] border-collapse">
            <thead>
              <tr className="border-b border-border">
                {["Score", "File / Offset", "Type", "Status", "Method", "Size", ""].map((h) => (
                  <th key={h} className="label-xs px-3 py-2 text-left">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((a) => (
                <tr
                  key={a.id}
                  onClick={() => setSelected(a)}
                  className="cursor-pointer border-b border-border/60 transition-colors hover:bg-surface-2"
                >
                  <td className="px-3 py-2.5">
                    <div className="flex items-center gap-2">
                      <span className="w-7 font-mono text-[12px] tabular-nums">{a.priority}</span>
                      <div className="h-1.5 w-16 bg-surface-2">
                        <div
                          className="h-1.5 bg-primary"
                          style={{ width: `${a.priority}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="px-3 py-2.5">
                    <p className="text-sm">{a.name}</p>
                    <p className="font-mono text-[11px] text-muted-foreground">{hex(a.offset)}</p>
                  </td>
                  <td className="px-3 py-2.5 font-mono text-[12px]">{a.type}</td>
                  <td className="px-3 py-2.5">
                    <Badge tone={statusTone(a.status)}>
                      {a.status === "PARTIAL" ? `PARTIAL ${a.completeness}%` : a.status}
                    </Badge>
                  </td>
                  <td className="px-3 py-2.5 font-mono text-[11px] text-muted-foreground">
                    {a.method}
                  </td>
                  <td className="px-3 py-2.5 font-mono text-[12px] tabular-nums">{a.sizeKb} KB</td>
                  <td className="px-3 py-2.5 text-right">
                     {a.name === "recovered_photo_B14.jpg" ? <Btn variant="solid" onClick={(e) => { e.stopPropagation(); setCompare(true); }}><GitCompareArrows size={13}/> Compare reassembly</Btn> : <Btn variant="solid">Inspect</Btn>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {selected && <EvidencePanel artifact={selected} onClose={() => setSelected(null)} />}
       {compare && <div className="fixed inset-0 z-[60] grid place-items-center bg-background/85 p-3 sm:p-6" role="dialog" aria-modal="true" aria-label="Compare reassembly"><div className="max-h-[95vh] w-full max-w-5xl overflow-y-auto border border-border-strong bg-surface shadow-2xl"><header className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-4"><div><p className="label-xs text-primary">Fragment reconstruction / B₁₂ → B₈₉</p><h2 className="mt-1 text-lg font-semibold">recovered_photo_B14.jpg</h2></div><Button variant="outline" size="icon" title="Close comparison" aria-label="Close comparison" onClick={() => setCompare(false)}><X size={16}/></Button></header>
         <div className="flex gap-2 border-b border-border p-4 sm:hidden"><Btn variant={!after ? "solid" : "ghost"} onClick={() => setAfter(false)}>Before</Btn><Btn variant={after ? "solid" : "ghost"} onClick={() => setAfter(true)}>After</Btn></div>
         <div className="grid gap-px bg-border sm:grid-cols-2"><div className={`${after ? "hidden sm:block" : "block"} bg-surface p-4`}><p className="mb-3 text-sm font-medium">Traditional PhotoRec 7.1 <span className="ml-2 text-encrypted">/ BROKEN CARVE</span></p><div className="relative aspect-[3/2] overflow-hidden bg-background"><img src={reconstructedEvidence} width={1200} height={800} loading="lazy" alt="Incomplete recovered office exterior photograph" className="h-full w-full object-cover"/><div className="absolute inset-x-0 bottom-0 grid h-[48%] place-items-center bg-unalloc/95 font-mono text-xs text-muted-foreground">CORRUPTED DATA / NO DECODER OUTPUT</div></div><p className="mt-3 font-mono text-xs text-encrypted">Decoder Error: Bitstream Sync Lost at Byte 28,672</p></div>
         <div className={`${after ? "block" : "hidden sm:block"} bg-surface p-4`}><p className="mb-3 text-sm font-medium">Evidra RECON <span className="ml-2 text-intact">/ RECONSTRUCTED</span></p><img src={reconstructedEvidence} width={1200} height={800} loading="lazy" alt="Complete reconstructed office exterior photograph" className="aspect-[3/2] w-full object-cover"/><p className="mt-3 font-mono text-xs text-intact">Stitched fragment B₁₂ to B₈₉ via Bifragment Gap Carving · Pillow verified</p></div></div>
         <div className="border-t border-border px-5 py-3 text-xs text-muted-foreground">Illustrative comparison using simulated evidence; not an actual forensic recovery.</div>
       </div></div>}
    </Shell>
  );
}

function EvidencePanel({ artifact, onClose }: { artifact: Artifact; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex justify-end">
       <Button variant="ghost" aria-label="Close" onClick={onClose} className="h-full flex-1 rounded-none bg-background/70 backdrop-blur-[2px]" />
      <aside className="flex h-full w-full max-w-xl flex-col overflow-y-auto border-l border-border-strong bg-surface">
        <header className="sticky top-0 flex items-start justify-between gap-4 border-b border-border bg-surface px-4 py-3">
          <div>
            <h2 className="font-mono text-sm">{artifact.name}</h2>
            <p className="label-xs mt-1">
              {artifact.id} · {hex(artifact.offset)} · {artifact.method}
            </p>
          </div>
          <Btn onClick={onClose}>Close</Btn>
        </header>

        <div className="space-y-4 p-4">
          <div className="flex flex-wrap gap-2">
            <Badge tone={statusTone(artifact.status)}>
              {artifact.status === "PARTIAL" ? `PARTIAL ${artifact.completeness}%` : artifact.status}
            </Badge>
            <Badge tone="primary">{artifact.type}</Badge>
            <Badge tone="muted">{artifact.sizeKb} KB</Badge>
          </div>

          <div>
            <p className="label-xs mb-2">Decoded preview</p>
            <div className="rounded-sm border border-border bg-background p-3">
              {artifact.status === "ENCRYPTED" ? (
                <p className="py-8 text-center font-mono text-[12px] text-encrypted">
                  DECODE BLOCKED — cipher-grade entropy across payload region
                </p>
               ) : artifact.name === "recovered_photo_B14.jpg" ? (
                 <img src={reconstructedEvidence} width={1200} height={800} loading="lazy" alt="Reconstructed office exterior evidence preview" className="w-full object-cover" />
               ) : artifact.type === "JPEG" || artifact.type === "PNG" ? (
                <div
                  className="grid h-40 place-items-center rounded-sm"
                  style={{
                    background:
                      "repeating-linear-gradient(135deg, var(--color-surface-2) 0 12px, var(--color-surface) 12px 24px)",
                  }}
                >
                  <div
                    className="h-32 w-56 border border-border-strong bg-background"
                    style={{
                      backgroundImage:
                        "linear-gradient(180deg, var(--color-primary) 0%, var(--color-document) 60%, transparent 60%)",
                      opacity: artifact.completeness / 100,
                    }}
                  />
                </div>
              ) : (
                <p className="font-mono text-[12px] leading-relaxed text-muted-foreground">
                  {artifact.textPreview}
                </p>
              )}
            </div>
          </div>

          <div>
            <p className="label-xs mb-2">Per-block entropy strip (4 KB chunks)</p>
            <div className="flex h-14 items-end gap-px rounded-sm border border-border bg-background p-1.5">
              {artifact.entropyStrip.map((e, i) => (
                <div
                  key={i}
                  title={e.toFixed(2)}
                  className="flex-1"
                  style={{
                    height: `${(e / 8) * 100}%`,
                    background: e > 7.4 ? "var(--color-encrypted)" : "var(--color-intact)",
                  }}
                />
              ))}
            </div>
            {artifact.status === "ENCRYPTED" && (
              <p className="mt-2 font-mono text-[11px] text-encrypted">
                Alternating high/low entropy → intermittent ransomware encryption
              </p>
            )}
          </div>

          <div>
            <p className="label-xs mb-2">Deterministic validation log</p>
            <ul className="divide-y divide-border rounded-sm border border-border">
              {artifact.validation.map((v) => (
                <li key={v.label} className="flex items-center justify-between px-3 py-2">
                  <span className="text-[12px]">{v.label}</span>
                  <span
                    className={`font-mono text-[11px] ${v.ok ? "text-intact" : "text-partial"}`}
                  >
                    {v.value}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <div className="space-y-2 rounded-sm border border-border bg-surface-2 p-3 font-mono text-[11px]">
            <p className="break-all">
              <span className="text-muted-foreground">SHA-256 </span>
              {artifact.sha256}
            </p>
            <p className="break-all">
              <span className="text-muted-foreground">TLSH </span>
              {artifact.tlsh}
            </p>
          </div>
        </div>
      </aside>
    </div>
  );
}
