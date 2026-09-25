import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { ArrowRight, HardDriveDownload, ShieldCheck, UploadCloud, X } from "lucide-react";
import { toast } from "sonner";
import { Badge, Btn } from "@/components/ui/primitives";
import { Button } from "@/components/ui/button";
import { DEMO_CASES } from "@/lib/demo-cases";

export const Route = createFileRoute("/locker")({
  head: () => ({ meta: [
    { title: "Evidence Locker — Evidra RECON" },
    { name: "description", content: "Select a forensic case or preview the disk image ingestion workflow in Evidra RECON." },
    { property: "og:title", content: "Evidence Locker — Evidra RECON" },
    { property: "og:description", content: "Forensic case selection and disk image triage workspace." },
    { property: "og:type", content: "website" }, { name: "twitter:card", content: "summary_large_image" },
  ] }),
  component: Locker,
});

function Locker() {
  const navigate = useNavigate();
  const [ingest, setIngest] = useState(false);
  const [step, setStep] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const [profile, setProfile] = useState("Standard triage");
  const [started] = useState(() => Date.now());
  const [minutes, setMinutes] = useState(0);
  // Display-only timer; no authorization or persistent audit claim.
  useEffect(() => { const id = window.setInterval(() => setMinutes(Math.floor((Date.now() - started) / 60000)), 30000); return () => clearInterval(id); }, [started]);
  return <div className="min-h-screen bg-background">
    <header className="border-b border-border bg-surface px-5 py-4 lg:px-10"><div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4">
      <div><p className="text-lg font-semibold">EVIDRA <span className="text-primary">/ RECON</span></p><p className="text-xs text-muted-foreground">Evidence locker</p></div>
      <div className="flex flex-wrap items-center gap-3"><span className="text-xs text-muted-foreground">J. Bhuvanesh · Senior Examiner <span className="font-mono">/ {minutes}m session</span></span><Btn variant="solid" onClick={() => { setIngest(true); setStep(0); }}><HardDriveDownload size={14}/> Ingest New Disk Image</Btn></div>
    </div></header>
    <main className="mx-auto max-w-7xl px-5 py-10 lg:px-10"><div className="mb-8 flex flex-wrap items-end justify-between gap-4"><div><p className="label-xs text-primary">Case selection</p><h1 className="mt-2 text-3xl font-semibold">Evidence locker</h1><p className="mt-2 text-sm text-muted-foreground">Select an investigation to open its workspace.</p></div><Badge tone="intact"><ShieldCheck size={13}/> Read-only workspace</Badge></div>
      <div className="grid gap-4 lg:grid-cols-3">{DEMO_CASES.map((c) => <Button key={c.id} variant="outline" onClick={() => { if (c.id === "CASE-2026-ALPHA") void navigate({ to: "/" }); else toast.info(`${c.id} is a case selection preview; only Alpha has investigation data.`); }} className="group h-auto min-h-64 w-full flex-col items-stretch justify-between whitespace-normal rounded-sm border-border bg-surface p-5 text-left shadow-none hover:bg-surface-2">
        <div><div className="flex items-center justify-between gap-2"><span className="font-mono text-xs text-primary">{c.id}</span><Badge tone={c.tone}>{c.urgency}</Badge></div><h2 className="mt-8 text-lg font-semibold leading-snug">{c.title}</h2><p className="mt-3 font-mono text-xs text-muted-foreground">{c.image} · {c.size}</p></div>
        <div><div className="flex justify-between gap-2 border-t border-border pt-4 text-xs text-muted-foreground"><span>{c.recovered}</span><span>{c.integrity}</span></div><div className="mt-4 flex items-center justify-between text-xs"><span className="text-muted-foreground">{c.updated}</span><ArrowRight size={16} className="text-primary transition-transform group-hover:translate-x-1"/></div></div>
      </Button>)}</div>
    </main>
    {ingest && <div className="fixed inset-0 z-50 grid place-items-center bg-background/80 p-4" role="dialog" aria-modal="true" aria-label="Ingest disk image"><div className="w-full max-w-lg border border-border-strong bg-surface p-5 shadow-2xl"><div className="flex justify-between gap-3"><div><p className="label-xs text-primary">Image ingestion</p><h2 className="mt-1 text-xl font-semibold">New disk image</h2></div><Btn onClick={() => setIngest(false)}><X size={15}/></Btn></div><div className="my-6 flex gap-2">{["Upload", "SHA-256", "Triage profile"].map((s,i)=><div key={s} className={`flex-1 border-t-2 pt-2 text-xs ${step===i ? "border-primary text-foreground" : "border-border text-muted-foreground"}`}>{`0${i+1}`} {s}</div>)}</div>
      {step===0 && <label className="flex min-h-40 cursor-pointer flex-col items-center justify-center gap-3 border border-dashed border-border-strong bg-background p-5 text-center"><UploadCloud className="text-primary"/><span className="text-sm">{file?.name ?? "Choose a .dd, .raw, or .E01 image"}</span><span className="text-xs text-muted-foreground">Local preview only · no file is uploaded</span><input className="sr-only" type="file" accept=".dd,.raw,.E01,.e01" onChange={(e)=>setFile(e.target.files?.[0] ?? null)}/></label>}
      {step===1 && <div className="border border-border bg-background p-5"><p className="text-sm font-medium">Hash verification preview</p><p className="mt-2 text-xs text-muted-foreground">{file?.name} · {file ? (file.size/1024/1024).toFixed(2) : "0"} MB</p><p className="mt-5 text-xs text-partial">No cryptographic verification is performed in this frontend demo.</p></div>}
      {step===2 && <div><label htmlFor="triage-profile" className="text-sm">Triage profile</label><select id="triage-profile" value={profile} onChange={(e)=>setProfile(e.target.value)} className="mt-2 w-full border border-border bg-background p-3 text-sm"><option>Standard triage</option><option>Ransomware investigation</option><option>Document recovery</option></select><p className="mt-4 text-xs text-muted-foreground">This preview does not process or retain disk images.</p></div>}
      <div className="mt-6 flex justify-between"><Btn onClick={() => step ? setStep(step-1) : setIngest(false)}>{step ? "Back" : "Cancel"}</Btn><Btn variant="solid" onClick={() => { if (step<2) setStep(step+1); else { setIngest(false); toast.info("Ingestion preview complete. No image was processed."); } }} className={!file ? "pointer-events-none opacity-40" : ""}>{step===2 ? "Finish preview" : "Continue"}</Btn></div>
    </div></div>}
  </div>;
}
