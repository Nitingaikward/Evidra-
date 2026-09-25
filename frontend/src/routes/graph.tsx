import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Shell } from "@/components/Shell";
import { Badge, Panel } from "@/components/ui/primitives";
import { useGraph } from "@/lib/api";
import { REVISION_TIMELINE } from "@/lib/forensic-data";

export const Route = createFileRoute("/graph")({
  head: () => ({
    meta: [
      { title: "Evidence Relationship Graph — Evidra RECON" },
      {
        name: "description",
        content:
          "TLSH fuzzy-hash clustering of recovered evidence: exact duplicates, near-duplicate document revisions and fragment reassembly links.",
      },
      { property: "og:title", content: "Evidence Relationship Graph — Evidra RECON" },
      {
        property: "og:description",
        content: "Explore duplicate, near-duplicate and fragment-to-parent links across recovered files.",
      },
      { property: "og:type", content: "website" }, { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: GraphView,
});

const EDGE_STYLE = {
  duplicate: { stroke: "var(--color-intact)", dash: "0" },
  "near-duplicate": { stroke: "var(--color-primary)", dash: "4 3" },
  reassembly: { stroke: "var(--color-partial)", dash: "1 4" },
} as const;

function GraphView() {
  const { data } = useGraph();
  const [active, setActive] = useState<string | null>(null);
  if (!data) return null;

  const activeNode = data.nodes.find((n) => n.id === active);
  const cluster = activeNode?.cluster;

  return (
    <Shell title="Relationship Graph">
      <div className="grid gap-4 xl:grid-cols-[1fr_380px]">
        <Panel title="TLSH similarity network · 18 nodes">
          <svg viewBox="0 0 100 100" className="h-[620px] w-full grid-lines rounded-sm border border-border bg-background">
            {data.edges.map((e, i) => {
               const s = data.nodes.find((n) => n.id === e.source);
               const t = data.nodes.find((n) => n.id === e.target);
               if (!s || !t) return null;
              const dim = cluster !== undefined && s.cluster !== cluster;
              const st = EDGE_STYLE[e.kind];
              return (
                <line
                  key={i}
                  x1={s.x}
                  y1={s.y}
                  x2={t.x}
                  y2={t.y}
                  stroke={st.stroke}
                  strokeWidth={0.22}
                  strokeDasharray={st.dash}
                  opacity={dim ? 0.1 : 0.7}
                />
              );
            })}
            {data.nodes.map((n) => {
              const dim = cluster !== undefined && n.cluster !== cluster;
              const fill =
                n.status === "ENCRYPTED"
                  ? "var(--color-encrypted)"
                  : n.status === "PARTIAL"
                    ? "var(--color-partial)"
                    : n.kind === "fragment"
                      ? "var(--color-document)"
                      : "var(--color-primary)";
              return (
                <g key={n.id} opacity={dim ? 0.15 : 1} onClick={() => setActive(n.id)} className="cursor-pointer">
                  <circle
                    cx={n.x}
                    cy={n.y}
                    r={n.id === active ? 1.9 : 1.3}
                    fill={fill}
                    stroke="var(--color-background)"
                    strokeWidth={0.2}
                  />
                  <text x={n.x + 2.2} y={n.y + 0.6} fontSize={1.5} fill="var(--color-muted-foreground)">
                    {n.label}
                  </text>
                </g>
              );
            })}
          </svg>

          <div className="mt-3 flex flex-wrap gap-4 font-mono text-[11px] text-muted-foreground">
            <span className="flex items-center gap-2">
              <span className="h-px w-6 bg-intact" /> Exact duplicate (SHA-256)
            </span>
            <span className="flex items-center gap-2">
              <span className="h-px w-6 border-t border-dashed border-primary" /> Near-duplicate (TLSH)
            </span>
            <span className="flex items-center gap-2">
              <span className="h-px w-6 border-t border-dotted border-partial" /> Fragment → parent
            </span>
          </div>
        </Panel>

        <div className="space-y-4">
          <Panel title="Selected node">
            {!activeNode ? (
              <p className="py-10 text-center font-mono text-[12px] text-muted-foreground">
                Click a node to highlight its cluster.
              </p>
            ) : (
              <div className="space-y-3">
                <p className="font-mono text-sm">{activeNode.label}</p>
                <div className="flex gap-2">
                  <Badge tone="primary">{activeNode.id}</Badge>
                  <Badge tone="muted">cluster {activeNode.cluster}</Badge>
                </div>
                <ul className="divide-y divide-border rounded-sm border border-border">
                  {data.edges
                    .filter((e) => e.source === activeNode.id || e.target === activeNode.id)
                    .map((e, i) => (
                      <li key={i} className="flex items-center justify-between px-3 py-2 font-mono text-[11px]">
                        <span className="text-muted-foreground uppercase">{e.kind}</span>
                        <span>{e.weight}% similar</span>
                      </li>
                    ))}
                </ul>
              </div>
            )}
          </Panel>

          <Panel title="Document version timeline">
            <ol className="relative space-y-4 border-l border-border pl-5">
              {REVISION_TIMELINE.map((r) => (
                <li key={r.label} className="relative">
                  <span className="absolute -left-[23px] top-1.5 size-2 rounded-full border border-primary bg-background" />
                  <p className="font-mono text-[11px] text-muted-foreground">{r.at}</p>
                  <p className="text-sm">{r.label}</p>
                  <p className="font-mono text-[11px] text-primary">{r.note}</p>
                </li>
              ))}
            </ol>
          </Panel>
        </div>
      </div>
    </Shell>
  );
}
