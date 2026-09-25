import { useState } from "react";
import { CUSTODY_LOG } from "@/lib/forensic-data";
import { Btn } from "@/components/ui/primitives";

export function CustodyDrawer() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Btn onClick={() => setOpen(true)}>
        <span className="size-1.5 rounded-full bg-intact" />
        Chain of Custody
      </Btn>

      {open && (
        <div className="fixed inset-0 z-50 flex justify-end no-print">
          <button
            aria-label="Close audit log"
            onClick={() => setOpen(false)}
            className="flex-1 bg-background/70 backdrop-blur-[2px]"
          />
          <aside className="flex h-full w-full max-w-md flex-col border-l border-border-strong bg-surface">
            <header className="flex items-center justify-between border-b border-border px-4 py-3">
              <div>
                <h2 className="font-mono text-sm tracking-wide">CHAIN-OF-CUSTODY AUDIT LOG</h2>
                <p className="label-xs mt-1">Append-only · session SESS-7A21-FF09</p>
              </div>
              <Btn onClick={() => setOpen(false)}>Close</Btn>
            </header>
            <div className="flex-1 overflow-y-auto p-4">
              <ol className="relative space-y-0 border-l border-border pl-5">
                {CUSTODY_LOG.map((e, i) => (
                  <li key={i} className="relative pb-5">
                    <span className="absolute -left-[23px] top-1.5 size-2 rounded-full border border-primary bg-background" />
                    <p className="font-mono text-[11px] text-muted-foreground">{e.at}</p>
                    <p className="mt-0.5 text-sm">{e.action}</p>
                    <p className="mt-1 font-mono text-[11px] text-muted-foreground">
                      {e.actor} · verify {e.hash}
                    </p>
                  </li>
                ))}
              </ol>
            </div>
          </aside>
        </div>
      )}
    </>
  );
}
