import type { MouseEvent, ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export function Panel({
  title,
  right,
  children,
  className,
}: {
  title?: string;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("panel", className)}>
      {title && (
        <header className="flex items-center justify-between gap-3 border-b border-border px-4 py-2.5">
          <h2 className="label-xs">{title}</h2>
          {right}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

const TONES = {
  intact: "text-intact border-intact/40 bg-intact/10",
  partial: "text-partial border-partial/40 bg-partial/10",
  encrypted: "text-encrypted border-encrypted/40 bg-encrypted/10",
  primary: "text-primary border-primary/40 bg-primary/10",
  document: "text-document border-document/40 bg-document/10",
  muted: "text-muted-foreground border-border bg-surface-2",
} as const;

export type Tone = keyof typeof TONES;

export function Badge({
  tone = "muted",
  children,
  className,
}: {
  tone?: Tone;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 font-mono text-[11px] tracking-wider uppercase",
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function statusTone(status: string): Tone {
  switch (status) {
    case "FULL":
      return "intact";
    case "PARTIAL":
      return "partial";
    case "ENCRYPTED":
      return "encrypted";
    case "FRAGMENT":
      return "document";
    default:
      return "muted";
  }
}

export function Stat({
  label,
  value,
  sub,
  tone = "primary",
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: Tone;
}) {
  return (
    <div className="panel relative overflow-hidden px-4 py-3.5">
      <div
        className={cn("absolute inset-y-0 left-0 w-0.5", {
          "bg-primary": tone === "primary",
          "bg-intact": tone === "intact",
          "bg-partial": tone === "partial",
          "bg-encrypted": tone === "encrypted",
          "bg-document": tone === "document",
          "bg-border-strong": tone === "muted",
        })}
      />
      <p className="label-xs">{label}</p>
      <p className="mt-1.5 font-mono text-2xl leading-none tabular-nums">{value}</p>
      {sub && <p className="mt-1.5 font-mono text-[11px] text-muted-foreground">{sub}</p>}
    </div>
  );
}

export function Btn({
  children,
  onClick,
  variant = "ghost",
  className,
  type = "button",
}: {
  children: ReactNode;
  onClick?: (event: MouseEvent<HTMLButtonElement>) => void;
  variant?: "ghost" | "solid" | "danger";
  className?: string;
  type?: "button" | "submit";
}) {
  return (
    <Button
      type={type}
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-2 rounded-sm border px-3 py-1.5 font-mono text-[11px] tracking-wider uppercase transition-colors",
        variant === "ghost" &&
          "border-border bg-surface-2 text-muted-foreground hover:border-border-strong hover:text-foreground",
        variant === "solid" &&
          "border-primary/50 bg-primary/15 text-primary hover:bg-primary/25",
        variant === "danger" &&
          "border-encrypted/50 bg-encrypted/10 text-encrypted hover:bg-encrypted/20",
        className,
      )}
    >
      {children}
    </Button>
  );
}
