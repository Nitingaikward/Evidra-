import { createFileRoute } from "@tanstack/react-router";
import { Shell } from "@/components/Shell";
import { toast } from "sonner";
import { Badge, Btn, Panel, statusTone } from "@/components/ui/primitives";
import { useArtifacts } from "@/lib/api";
import {
  AI_BRIEF,
  CASE,
  CUSTODY_LOG,
  KPIS,
  PII_FINDINGS,
  hex,
} from "@/lib/forensic-data";

export const Route = createFileRoute("/report")({
  head: () => ({
    meta: [
      { title: "Court-Ready Case Report — Evidra RECON" },
      {
        name: "description",
        content:
          "Exportable forensic case summary with chain of custody, hash verification, artifact inventory and AI-assisted triage brief.",
      },
      { property: "og:title", content: "Court-Ready Case Report — Evidra RECON" },
      {
        property: "og:description",
        content: "Printable forensic report with custody table, hashes and itemized artifact inventory.",
      },
      { property: "og:type", content: "website" }, { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Report,
});

function Report() {
  const { data: artifacts } = useArtifacts();

  function downloadJson() {
    const blob = new Blob(
      [JSON.stringify({ case: CASE, kpis: KPIS, custody: CUSTODY_LOG, artifacts }, null, 2)],
      { type: "application/json" },
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${CASE.id}-evidence-package.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("JSON data model exported");
  }

  function downloadHtml() {
    const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>${CASE.id} — Evidra RECON dossier</title><style>body{font:14px Arial,sans-serif;max-width:960px;margin:40px auto;color:#17202b;line-height:1.5}table{width:100%;border-collapse:collapse}td,th{border:1px solid #bbb;padding:8px;text-align:left}h1,h2{border-bottom:1px solid #777;padding-bottom:8px}.no-print,button{display:none}</style></head><body><h1>EVIDRA RECON — ${CASE.id}</h1><p>Illustrative demo dossier · not a certified forensic report</p><h2>Image integrity</h2><p>Image: ${CASE.imageName} · SHA-256: ${CASE.sha256}</p><h2>Chain of custody (simulated)</h2><table><thead><tr><th>Time</th><th>Actor</th><th>Event</th><th>Hash</th></tr></thead><tbody>${CUSTODY_LOG.map(e => `<tr><td>${e.at}</td><td>${e.actor}</td><td>${e.action}</td><td>${e.hash}</td></tr>`).join("")}</tbody></table><h2>Artifact inventory</h2><table><thead><tr><th>ID</th><th>File</th><th>Status</th><th>SHA-256</th></tr></thead><tbody>${(artifacts ?? []).map(a => `<tr><td>${a.id}</td><td>${a.name}</td><td>${a.status}</td><td>${a.sha256}</td></tr>`).join("")}</tbody></table><h2>Examiner signature</h2><p>${CASE.examiner} · Signature: ____________________ · Date: ____________________</p></body></html>`;
    const url = URL.createObjectURL(new Blob([html], { type: "text/html" }));
    const link = document.createElement("a"); link.href = url; link.download = `${CASE.id}-dossier.html`; link.click(); URL.revokeObjectURL(url);
    toast.success("HTML dossier exported");
  }

  return (
     <Shell title="Case Report">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3 no-print">
        <div>
          <h1 className="text-lg font-semibold">CASE DOSSIER PREVIEW</h1>
           <p className="label-xs mt-1">{CASE.id} · simulated demonstration data</p>
        </div>
         <div className="flex flex-wrap gap-2">
           <Btn onClick={downloadHtml}>Export HTML dossier</Btn>
           <Btn onClick={downloadJson}>Export JSON data model</Btn>
          <Btn variant="solid" onClick={() => window.print()}>
             Print PDF
          </Btn>
        </div>
      </div>

       <div id="dossier-content"><div className="mb-4 border-b border-border pb-4"><p className="text-sm font-semibold">EVIDRA RECON · DIGITAL EVIDENCE EXAMINATION</p><p className="mt-1 text-xs text-muted-foreground">Case {CASE.id} · Examiner {CASE.examiner} · Signature ____________________ · Date ____________________</p><p className="mt-2 text-xs text-partial">Demonstration dossier — simulated findings, not certified evidence.</p></div>
       <Panel title="AI investigator brief" className="mb-4">
        <Badge tone="partial" className="mb-3">
          Simulated investigator brief / demonstration data
        </Badge>
        <p className="text-sm leading-relaxed">{AI_BRIEF}</p>
        <p className="label-xs mt-3">Detected PII</p>
        <ul className="mt-2 divide-y divide-border rounded-sm border border-border">
          {PII_FINDINGS.map((p) => (
            <li key={p.value} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
              <span className="font-mono text-[11px] text-muted-foreground uppercase">{p.kind}</span>
              <span className="font-mono text-[12px]">{p.value}</span>
              <span className="font-mono text-[11px] text-primary">{p.source}</span>
            </li>
          ))}
        </ul>
      </Panel>
       </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Image integrity">
          <dl className="space-y-2 font-mono text-[12px]">
            <div className="flex justify-between gap-3 border-b border-border/60 pb-2">
              <dt className="label-xs">Pre-analysis SHA-256</dt>
              <dd className="break-all text-right text-intact">{CASE.sha256}</dd>
            </div>
            <div className="flex justify-between gap-3 border-b border-border/60 pb-2">
              <dt className="label-xs">Post-analysis SHA-256</dt>
              <dd className="break-all text-right text-intact">{CASE.sha256}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="label-xs">Mount mode</dt>
              <dd>READ-ONLY MMAP</dd>
            </div>
          </dl>
        </Panel>

        <Panel title="Chain of custody">
          <table className="w-full border-collapse font-mono text-[11px]">
            <tbody>
              {CUSTODY_LOG.map((e, i) => (
                <tr key={i} className="border-b border-border/60">
                  <td className="py-2 pr-3 text-muted-foreground">{e.at}</td>
                  <td className="py-2 pr-3 text-primary">{e.actor}</td>
                  <td className="py-2">{e.action}</td>
                  <td className="py-2 pl-3 text-right text-muted-foreground">{e.hash}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      </div>

      <Panel title={`Artifact inventory · ${artifacts?.length ?? 0} items`} className="mt-4">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[820px] border-collapse">
            <thead>
              <tr className="border-b border-border">
                {["ID", "File", "Offset", "Type", "Status", "Method", "SHA-256"].map((h) => (
                  <th key={h} className="label-xs px-2 py-2 text-left">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {artifacts?.map((a) => (
                <tr key={a.id} className="border-b border-border/60">
                  <td className="px-2 py-2 font-mono text-[11px] text-primary">{a.id}</td>
                  <td className="px-2 py-2 text-[12px]">{a.name}</td>
                  <td className="px-2 py-2 font-mono text-[11px]">{hex(a.offset)}</td>
                  <td className="px-2 py-2 font-mono text-[11px]">{a.type}</td>
                  <td className="px-2 py-2">
                    <Badge tone={statusTone(a.status)}>{a.status}</Badge>
                  </td>
                  <td className="px-2 py-2 font-mono text-[11px] text-muted-foreground">{a.method}</td>
                  <td className="px-2 py-2 font-mono text-[11px] text-muted-foreground">
                    {a.sha256.slice(0, 16)}…
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </Shell>
  );
}
