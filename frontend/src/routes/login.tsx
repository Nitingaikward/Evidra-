import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { CASE } from "@/lib/forensic-data";
import { ShieldCheck, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "Examiner Sign In — Evidra RECON" },
      { name: "description", content: "Secure examiner sign-in for the Evidra RECON forensic workstation." },
      { property: "og:title", content: "Examiner Sign In — Evidra RECON" },
      { property: "og:description", content: "Sign in to open the active forensic case dashboard." },
      { property: "og:type", content: "website" }, { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Login,
});

function Login() {
  const navigate = useNavigate();
  const [name, setName] = useState("J. Bhuvanesh");
  const [badge, setBadge] = useState("EX-8941-DFIR");
  const [agency, setAgency] = useState("Federal Cybercrime Division");
  const [warrant, setWarrant] = useState("WRT-2026-0925-ALPHA");
  const go = () => navigate({ to: "/locker" });

  return (
    <div className="grid min-h-screen place-items-center bg-background px-4">
       <div className="w-full max-w-md rounded-sm border border-border bg-surface p-7">
        <div className="flex items-center gap-2.5">
          <span className="grid size-8 place-items-center rounded-sm border border-primary/50 bg-primary/10 font-mono text-[11px] text-primary">
            EV
          </span>
          <span className="font-mono text-sm tracking-[0.2em]">EVIDRA</span>
          <span className="label-xs">RECON</span>
        </div>
         <h1 className="mt-7 text-xl font-semibold">Examiner sign in</h1>
         <p className="mt-1 text-[13px] text-muted-foreground">Digital Evidence Reconstruction Suite</p>
         <p className="mt-5 flex items-center gap-2 border border-intact/30 bg-intact/10 px-3 py-2 text-xs text-intact"><ShieldCheck size={14}/> HARDWARE WRITE-BLOCK ACTIVE <span className="ml-auto text-muted-foreground">Demo indicator</span></p>

        <form
          className="mt-6 space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            go();
          }}
        >
          <label className="block">
             <span className="label-xs">Examiner full name</span>
            <input
               value={name}
               onChange={(e) => setName(e.target.value)}
               required maxLength={100}
              className="mt-1.5 w-full rounded-sm border border-border bg-background px-3 py-2 font-mono text-[12px] outline-none focus:border-primary/60"
            />
          </label>
          <label className="block">
             <span className="label-xs">Badge / Agent ID</span>
            <input
               value={badge}
               onChange={(e) => setBadge(e.target.value)}
               required maxLength={40}
              className="mt-1.5 w-full rounded-sm border border-border bg-background px-3 py-2 font-mono text-[12px] outline-none focus:border-primary/60"
            />
          </label>
           <label className="block"><span className="label-xs">Agency / Lab</span><select value={agency} onChange={(e) => setAgency(e.target.value)} className="mt-1.5 w-full rounded-sm border border-border bg-background px-3 py-2 text-[12px]"><option>Federal Cybercrime Division</option><option>Enterprise Incident Response Lab</option></select></label>
           <label className="block"><span className="label-xs">Case authorization / warrant reference</span><input value={warrant} onChange={(e) => setWarrant(e.target.value)} required maxLength={80} className="mt-1.5 w-full rounded-sm border border-border bg-background px-3 py-2 font-mono text-[12px] outline-none focus:border-primary/60" /></label>
           <Button type="submit" className="w-full rounded-sm">Authenticate & Enter Case Locker</Button>
        </form>

        <div className="my-5 flex items-center gap-3">
          <span className="h-px flex-1 bg-border" />
          <span className="label-xs">or</span>
          <span className="h-px flex-1 bg-border" />
        </div>

         <Button onClick={() => { setName("J. Bhuvanesh"); setBadge("EX-8941-DFIR"); setAgency("Federal Cybercrime Division"); setWarrant("WRT-2026-0925-ALPHA"); void go(); }} variant="outline" className="w-full rounded-sm"><Zap size={15}/> 1-Click Quick Demo Login</Button>
         <p className="mt-3 text-center text-xs text-partial">Demo access only — this form does not authenticate or record custody.</p>
        <p className="mt-4 text-center font-mono text-[10px] text-muted-foreground">
          Opens {CASE.id} · {CASE.imageName}
        </p>
      </div>
    </div>
  );
}
