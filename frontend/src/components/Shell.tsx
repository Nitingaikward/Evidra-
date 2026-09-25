import { Link } from "@tanstack/react-router";
import { useState, type ReactNode } from "react";
import { CASE } from "@/lib/forensic-data";
import { Badge } from "@/components/ui/primitives";
import { CustodyDrawer } from "@/components/CustodyDrawer";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { LayoutDashboard, Grid2X2, Files, Network, FileText, Menu, Copy, ArrowLeftRight, Download, ShieldCheck } from "lucide-react";

const NAV = [
  { to: "/", label: "Overview & Dashboard", sub: "Benchmark", code: "01", icon: LayoutDashboard },
  { to: "/heatmap", label: "4 KB Disk Heatmap", sub: "Hex Inspector", code: "02", icon: Grid2X2 },
  { to: "/artifacts", label: "Evidence Explorer", sub: "Fragment Diff", code: "03", icon: Files },
  { to: "/graph", label: "Relationship Graph", sub: "TLSH Node Map", code: "04", icon: Network },
  { to: "/report", label: "Case Report", sub: "Court Dossier", code: "05", icon: FileText },
] as const;

export function Shell({ children, title }: { children: ReactNode; title?: string }) {
  const [copied, setCopied] = useState(false);
  const [open, setOpen] = useState(false);

  return (
    <div className="flex min-h-screen w-full bg-background">
      {open && (
         <Button
           variant="ghost"
          aria-label="Close menu"
          onClick={() => setOpen(false)}
          className="fixed inset-0 z-40 h-full w-full rounded-none bg-background/70 lg:hidden"
         />
      )}
      <aside
        className={`no-print fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-border bg-surface transition-transform lg:sticky lg:top-0 lg:h-screen lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
         <Link to="/locker" className="flex h-16 items-center gap-2.5 border-b border-border px-4">
          <span className="grid size-7 place-items-center rounded-sm border border-primary/50 bg-primary/10 font-mono text-[11px] text-primary">
            EV
          </span>
           <span className="text-sm font-semibold">EVIDRA</span>
          <span className="label-xs">RECON</span>
        </Link>

        <nav className="flex-1 space-y-1 p-3">
          <p className="label-xs px-2 pb-2">Workspace</p>
          {NAV.map((n) => (
            <Link
              key={n.to}
              to={n.to}
              onClick={() => setOpen(false)}
              activeOptions={{ exact: n.to === "/" }}
              activeProps={{ className: "border-primary/40 bg-primary/10 text-foreground" }}
              inactiveProps={{
                className: "border-transparent text-muted-foreground hover:bg-surface-2 hover:text-foreground",
              }}
              className="group flex items-start gap-3 rounded-sm border px-2.5 py-2 transition-colors"
            >
                 <n.icon size={16} className="mt-0.5 shrink-0 text-primary" />
              <span>
                <span className="block text-[13px] font-medium">{n.label}</span>
                 <span className="block text-[10px] text-muted-foreground">{n.code} / {n.sub}</span>
              </span>
            </Link>
          ))}
        </nav>

        <div className="border-t border-border p-3">
          <div className="flex items-center gap-2.5">
            <span className="grid size-8 place-items-center rounded-sm border border-border bg-surface-2 font-mono text-[11px]">
              JB
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[12px]">{CASE.examiner}</p>
               <p className="truncate text-[10px] text-muted-foreground">Senior Examiner</p>
            </div>
             <Link to="/login" className="text-[10px] uppercase text-muted-foreground hover:text-foreground">
               Logout
            </Link>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
         <header className="no-print sticky top-0 z-30 flex min-h-16 flex-wrap items-center gap-2 border-b border-border bg-background/95 px-4 py-2 backdrop-blur lg:px-8">
           <Button variant="outline" size="icon"
            onClick={() => setOpen(true)}
             className="shrink-0 rounded-sm lg:hidden"
            aria-label="Open menu"
          >
             <Menu size={17}/>
           </Button>
           <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-4 gap-y-1 text-[11px]">
            <span className="flex items-center gap-2">
              <span className="label-xs hidden sm:inline">Case</span>
               <span className="font-mono text-primary">{CASE.id}</span>
            </span>
            <span className="hidden items-center gap-2 md:flex">
              <span className="label-xs">Image</span>
               <span className="font-mono">{CASE.imageName}</span>
            </span>
             <Button variant="outline" size="sm"
              onClick={() => {
                void navigator.clipboard?.writeText(CASE.sha256);
                setCopied(true);
                 toast.success("SHA-256 copied");
                setTimeout(() => setCopied(false), 1400);
              }}
              title={CASE.sha256}
               className="hidden h-7 items-center gap-2 rounded-sm border-intact/40 bg-intact/10 px-2 text-intact hover:bg-intact/20 sm:flex"
            >
              <span className="text-[10px] tracking-wider">SHA-256</span>
               <span className="font-mono text-foreground">{CASE.sha256.slice(0, 12)}…{CASE.sha256.slice(-6)}</span>
               <Copy size={12}/><span className="sr-only">{copied ? "Copied" : "Copy"}</span>
             </Button>
          </div>
           <Badge tone="intact" className="hidden xl:inline-flex">
             <ShieldCheck size={12}/> Read-only demo (MMAP)
          </Badge>
          <CustodyDrawer />
           <Button asChild variant="outline" size="sm" className="h-8 rounded-sm"><Link to="/locker"><ArrowLeftRight size={14}/> <span className="hidden sm:inline">Switch case</span></Link></Button>
           <Button asChild size="sm" className="h-8 rounded-sm"><Link to="/report"><Download size={14}/> <span className="hidden sm:inline">Export dossier</span></Link></Button>
        </header>

         <main className="w-full min-w-0 flex-1 px-4 py-6 lg:px-8">
           {title && <div className="mb-6"><p className="label-xs text-primary">Investigation / {CASE.id}</p><h1 className="mt-1 text-2xl font-semibold">{title}</h1></div>}
          {children}
        </main>
      </div>
    </div>
  );
}
