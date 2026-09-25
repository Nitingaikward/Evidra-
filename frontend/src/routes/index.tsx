import { createFileRoute } from "@tanstack/react-router";
import { Shell } from "@/components/Shell";
import { Badge, Panel, Stat } from "@/components/ui/primitives";
import { useCaseOverview } from "@/lib/api";
import { CASE, CUSTODY_LOG } from "@/lib/forensic-data";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Case Overview — Evidra RECON Forensic Workstation" },
      {
        name: "description",
        content:
          "Evidra RECON case dashboard: disk image integrity, recovered artifact KPIs and Evidra vs PhotoRec recovery benchmarks.",
      },
      { property: "og:title", content: "Case Overview — Evidra RECON" },
      {
        property: "og:description",
        content: "Digital forensics case dashboard with integrity metrics and recovery benchmarks.",
      },
      { property: "og:type", content: "website" }, { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Overview,
});

function Overview() {
  const { data } = useCaseOverview();
  if (!data) return null;
  const { kpis, benchmarks } = data;

  return (
    <Shell title="Dashboard">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Scanned blocks" value="16,384" sub="4 KB cluster granularity" />
        <Stat label="Recovered files" value="42" sub="FS + carved + reassembled" tone="document" />
        <Stat label="Integrity score" value="94%" sub="CRC32 + decoder verified" tone="intact" />
        <Stat label="Ransomware patterns" value="3" sub="Intermittent encryption" tone="encrypted" />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Panel title="Evidra vs PhotoRec" className="lg:col-span-2">
          <div className="grid gap-px overflow-hidden rounded-sm border border-border bg-border sm:grid-cols-2">
            <div className="bg-surface-2 p-4">
              <p className="label-xs">Junk / corrupt output</p>
              <p className="mt-2 font-mono text-3xl text-primary">10×</p>
              <p className="mt-1 text-[13px] text-muted-foreground">less junk than PhotoRec</p>
              <div className="mt-4 space-y-2">
                <BenchBar label="EVIDRA" value={4} tone="primary" />
                <BenchBar label="PHOTOREC" value={40} tone="muted" />
              </div>
            </div>
            <div className="bg-surface-2 p-4">
              <p className="label-xs">Fragment reassembly</p>
              <p className="mt-2 font-mono text-3xl text-intact">80%</p>
              <p className="mt-1 text-[13px] text-muted-foreground">fragmented files rebuilt</p>
              <div className="mt-4 space-y-2">
                <BenchBar label="EVIDRA" value={80} tone="primary" />
                <BenchBar label="PHOTOREC" value={0} tone="muted" />
              </div>
            </div>
          </div>
          <p className="mt-3 font-mono text-[11px] text-muted-foreground">
            {benchmarks.length} benchmark metrics · engine pass {(CASE.engineMs / 1000).toFixed(2)}s · {kpis.scannedBlocks.toLocaleString()} blocks
          </p>
        </Panel>


        <Panel title="Acquisition record">
          <dl className="space-y-3 font-mono text-[12px]">
            <Row k="Image" v={CASE.imageName} />
            <Row k="Size" v={`${CASE.imageSizeMb} MB`} />
            <Row k="Acquired" v={CASE.acquired} />
            <Row k="Examiner" v={CASE.examiner} />
            <Row k="Clearance" v={CASE.clearance} />
            <Row k="Mount" v="MMAP / read-only" />
          </dl>
          <div className="mt-4 rounded-sm border border-border bg-surface-2 p-3">
            <p className="label-xs">Pre / post analysis hash</p>
            <p className="mt-2 break-all font-mono text-[11px] text-intact">{CASE.sha256}</p>
            <Badge tone="intact" className="mt-2">
              Unchanged
            </Badge>
          </div>
        </Panel>
      </div>

       <Panel title="Recent custody events · simulated" className="mt-4">
        <ul className="divide-y divide-border">
          {CUSTODY_LOG.slice(-4).map((e, i) => (
            <li key={i} className="flex flex-wrap items-center gap-x-4 gap-y-1 py-2.5 font-mono text-[12px]">
              <span className="text-muted-foreground">{e.at}</span>
              <span className="text-primary">{e.actor}</span>
              <span className="text-foreground">{e.action}</span>
              <span className="ml-auto text-muted-foreground">{e.hash}</span>
            </li>
          ))}
        </ul>
      </Panel>
    </Shell>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-border/60 pb-2">
      <dt className="label-xs">{k}</dt>
      <dd className="text-right">{v}</dd>
    </div>
  );
}

function BenchBar({ label, value, tone }: { label: string; value: number; tone: "primary" | "muted" }) {
  return (
    <div className="flex items-center gap-3">
      <span className="w-20 shrink-0 font-mono text-[11px] text-muted-foreground">{label}</span>
      <div className="h-3 flex-1 rounded-sm bg-surface-2">
        <div
          className={tone === "primary" ? "h-3 rounded-sm bg-primary" : "h-3 rounded-sm bg-unalloc"}
          style={{ width: `${Math.max(value, 1)}%` }}
        />
      </div>
      <span className="w-12 text-right font-mono text-[12px] tabular-nums">{value}%</span>
    </div>
  );
}
