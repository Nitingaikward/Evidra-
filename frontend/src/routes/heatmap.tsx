import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Shell } from "@/components/Shell";
import { Badge, Btn, Panel } from "@/components/ui/primitives";
import { Button } from "@/components/ui/button";
import { useBlocks, useHexDump } from "@/lib/api";
import {
  BLOCK_COLOR,
  BLOCK_SIZE,
  BLOCK_TYPES,
  hex,
  type BlockType,
} from "@/lib/forensic-data";

export const Route = createFileRoute("/heatmap")({
  head: () => ({
    meta: [
      { title: "Disk Heatmap & Hex Inspector — Evidra RECON" },
      {
        name: "description",
        content:
          "Interactive 4KB cluster heatmap with entropy, LightGBM classification confidence and a live hex/ASCII dump.",
      },
      { property: "og:title", content: "Disk Heatmap & Hex Inspector — Evidra RECON" },
      {
        property: "og:description",
        content: "Explore 16,384 disk clusters by classified block type, entropy and hex content.",
      },
      { property: "og:type", content: "website" }, { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Heatmap,
});

const ZOOM = [
  { label: "1×", size: 6 },
  { label: "2×", size: 10 },
  { label: "4×", size: 16 },
];

function Heatmap() {
  const { data: blocks } = useBlocks();
  const [filter, setFilter] = useState<BlockType | "ALL">("ALL");
  const [zoom, setZoom] = useState(1);
  const [selected, setSelected] = useState<number | null>(null);
  const { data: dump } = useHexDump(selected);

  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    blocks?.forEach((b) => (c[b.type] = (c[b.type] ?? 0) + 1));
    return c;
  }, [blocks]);

  const block = selected !== null ? blocks?.[selected] : undefined;
  const cell = ZOOM[zoom]?.size ?? 10;

  return (
    <Shell title="Disk Heatmap">
      <div>
        <Panel
          title="4 KB cluster map · 16,384 blocks"
          right={
            <div className="flex items-center gap-1">
              {ZOOM.map((z, i) => (
                <Btn key={z.label} variant={i === zoom ? "solid" : "ghost"} onClick={() => setZoom(i)}>
                  {z.label}
                </Btn>
              ))}
            </div>
          }
        >
          <div className="mb-3 flex flex-wrap items-center gap-1.5">
            <Btn variant={filter === "ALL" ? "solid" : "ghost"} onClick={() => setFilter("ALL")}>
              All
            </Btn>
            {BLOCK_TYPES.map((t) => (
              <Btn key={t} variant={filter === t ? "solid" : "ghost"} onClick={() => setFilter(t)}>
                <span className="size-2 rounded-[2px]" style={{ background: BLOCK_COLOR[t] }} />
                {t}
                <span className="text-muted-foreground">{counts[t] ?? 0}</span>
              </Btn>
            ))}
          </div>

          <div
            className="flex flex-wrap gap-px overflow-y-auto rounded-sm border border-border bg-background p-2"
            style={{ maxHeight: "calc(100vh - 260px)", minHeight: 360 }}
          >
            {blocks?.map((b) => {
              const dim = filter !== "ALL" && b.type !== filter;
              return (
                 <Button variant="ghost"
                  key={b.index}
                  title={`${hex(b.index * BLOCK_SIZE)} · ${b.type}`}
                  onClick={() => setSelected(b.index)}
                  style={{
                    width: cell,
                    height: cell,
                    background: BLOCK_COLOR[b.type],
                    opacity: dim ? 0.07 : selected === b.index ? 1 : 0.85,
                    outline: selected === b.index ? "1px solid var(--color-foreground)" : undefined,
                  }}
                   className="min-w-0 rounded-[1px] border-0 p-0 transition-opacity hover:opacity-100"
                />
              );
            })}
          </div>
        </Panel>

        {block && (
          <div className="fixed inset-0 z-50 flex justify-end">
             <Button variant="ghost" aria-label="Close" onClick={() => setSelected(null)} className="h-full flex-1 rounded-none bg-background/60" />
            <aside className="h-full w-full max-w-md overflow-y-auto border-l border-border-strong bg-surface">
              <header className="sticky top-0 flex items-center justify-between border-b border-border bg-surface px-4 py-3">
                <p className="label-xs">Block inspector</p>
                <Btn onClick={() => setSelected(null)}>Close</Btn>
              </header>
            <div className="space-y-4 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-mono text-lg">{hex(block.index * BLOCK_SIZE)}</p>
                  <p className="label-xs mt-1">
                    Sector {(block.index * 8).toLocaleString()} · block {block.index.toLocaleString()}
                  </p>
                </div>
                <Badge tone={block.type === "ENCRYPTED" ? "encrypted" : "primary"}>{block.type}</Badge>
              </div>

              <div>
                <p className="label-xs mb-2">LightGBM classification confidence</p>
                <div className="space-y-1.5">
                  {BLOCK_TYPES.map((t, i) => {
                    const v =
                      t === block.type
                        ? block.confidence
                        : Math.max(0.01, (1 - block.confidence) / (6 + i * 0.4));
                    return (
                      <div key={t} className="flex items-center gap-2">
                        <span className="w-20 font-mono text-[11px] text-muted-foreground">{t}</span>
                        <div className="h-2 flex-1 bg-surface-2">
                          <div
                            className="h-2"
                            style={{ width: `${v * 100}%`, background: BLOCK_COLOR[t] }}
                          />
                        </div>
                        <span className="w-11 text-right font-mono text-[11px] tabular-nums">
                          {(v * 100).toFixed(1)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-sm border border-border bg-surface-2 p-3">
                  <p className="label-xs">Shannon entropy</p>
                  <p className="mt-1 font-mono text-xl">{block.entropy.toFixed(2)}</p>
                  <div className="mt-2 h-1.5 bg-background">
                    <div
                      className="h-1.5"
                      style={{
                        width: `${(block.entropy / 8) * 100}%`,
                        background: block.entropy > 7.5 ? "var(--color-encrypted)" : "var(--color-primary)",
                      }}
                    />
                  </div>
                </div>
                <div className="rounded-sm border border-border bg-surface-2 p-3">
                  <p className="label-xs">Chi-square deviation</p>
                  <p className="mt-1 font-mono text-xl">{block.chiSquare}</p>
                  <p className="mt-2 font-mono text-[11px] text-muted-foreground">
                    {block.chiSquare < 400 ? "uniform → cipher-like" : "structured"}
                  </p>
                </div>
              </div>

              <div>
                <p className="label-xs mb-2">Hex dump · 16 bytes/row</p>
                <div className="max-h-64 overflow-auto rounded-sm border border-border bg-background p-2 font-mono text-[11px] leading-relaxed">
                  {dump?.map((r) => (
                    <div key={r.offset} className="flex gap-3 whitespace-pre">
                      <span className="text-primary">{r.offset}</span>
                      <span className="text-foreground">{r.bytes.join(" ")}</span>
                      <span className="text-muted-foreground">|{r.ascii}|</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            </aside>
          </div>
        )}
      </div>
    </Shell>
  );
}
