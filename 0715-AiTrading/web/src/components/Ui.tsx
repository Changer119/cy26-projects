import type { ReactNode } from "react";

import type { HealthStatus, TradeAction } from "../types";

interface SectionHeaderProps {
  readonly eyebrow: string;
  readonly title: string;
  readonly description: string;
  readonly aside?: ReactNode;
}

export function SectionHeader({ eyebrow, title, description, aside }: SectionHeaderProps) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <p className="text-[10px] font-semibold tracking-[0.25em] text-cyan-400">{eyebrow}</p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight">{title}</h2>
        <p className="mt-2 max-w-2xl text-sm text-slate-400">{description}</p>
      </div>
      {aside}
    </div>
  );
}

interface StatCardProps {
  readonly label: string;
  readonly value: string;
  readonly detail: string;
  readonly tone?: "neutral" | "positive" | "negative" | "warning";
}

export function StatCard({ label, value, detail, tone = "neutral" }: StatCardProps) {
  const valueTone =
    tone === "positive"
      ? "text-emerald-300"
      : tone === "negative"
        ? "text-rose-300"
        : tone === "warning"
          ? "text-amber-300"
          : "text-slate-100";
  return (
    <article className="rounded-lg border border-white/8 bg-white/[0.025] p-4">
      <p className="text-[10px] font-medium tracking-[0.18em] text-slate-500">{label}</p>
      <p className={`mt-3 font-mono text-xl font-semibold tabular-nums ${valueTone}`}>{value}</p>
      <p className="mt-2 text-xs text-slate-500">{detail}</p>
    </article>
  );
}

export function ActionPill({ action }: { readonly action: TradeAction }) {
  const style =
    action === "BUY"
      ? "border-emerald-400/25 bg-emerald-400/10 text-emerald-300"
      : action === "SELL"
        ? "border-rose-400/25 bg-rose-400/10 text-rose-300"
        : "border-slate-500/30 bg-slate-500/10 text-slate-300";
  return <span className={`rounded border px-2 py-1 font-mono text-[10px] ${style}`}>{action}</span>;
}

export function HealthPill({ status }: { readonly status: HealthStatus }) {
  const label = status === "healthy" ? "正常" : status === "degraded" ? "降级" : "不可用";
  const style =
    status === "healthy"
      ? "bg-emerald-400"
      : status === "degraded"
        ? "bg-amber-400"
        : "bg-rose-400";
  return (
    <span className="inline-flex items-center gap-2 text-xs text-slate-300">
      <span className={`h-1.5 w-1.5 rounded-full ${style}`} />
      {label}
    </span>
  );
}

export function EmptyState({ children }: { readonly children: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-white/10 px-5 py-10 text-center text-sm text-slate-500">
      {children}
    </div>
  );
}
