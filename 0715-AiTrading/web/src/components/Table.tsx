import type { ReactNode } from "react";

export function DataTable({ children }: { readonly children: ReactNode }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-white/8 bg-white/[0.02]">
      <table className="w-full min-w-[760px] border-collapse text-left text-sm">{children}</table>
    </div>
  );
}

export function TableHead({ children }: { readonly children: ReactNode }) {
  return (
    <thead className="border-b border-white/8 bg-white/[0.025] text-[10px] tracking-[0.16em] text-slate-500">
      <tr>{children}</tr>
    </thead>
  );
}

export function HeadCell({ children }: { readonly children: ReactNode }) {
  return <th className="px-4 py-3 font-medium whitespace-nowrap">{children}</th>;
}

export function BodyCell({ children }: { readonly children: ReactNode }) {
  return <td className="border-b border-white/5 px-4 py-3 align-middle text-slate-300">{children}</td>;
}
