import type { ReactNode } from "react";

import { formatMicros } from "../format";
import type { AccountSnapshot } from "../types";

export type ViewId = "today" | "portfolio" | "watchlist" | "orders" | "performance" | "health";

interface NavigationItem {
  readonly id: ViewId;
  readonly label: string;
  readonly code: string;
}

const navigation: readonly NavigationItem[] = [
  { id: "today", label: "今日", code: "01" },
  { id: "portfolio", label: "组合", code: "02" },
  { id: "watchlist", label: "自选股", code: "03" },
  { id: "orders", label: "交易日志", code: "04" },
  { id: "performance", label: "绩效", code: "05" },
  { id: "health", label: "数据健康", code: "06" },
];

interface DashboardShellProps {
  readonly view: ViewId;
  readonly onViewChange: (view: ViewId) => void;
  readonly account: AccountSnapshot | null;
  readonly unavailableCount: number;
  readonly children: ReactNode;
}

export function DashboardShell({
  view,
  onViewChange,
  account,
  unavailableCount,
  children,
}: DashboardShellProps) {
  return (
    <div className="min-h-screen bg-[#07101b] text-slate-100">
      <div className="mx-auto grid min-h-screen max-w-[1680px] lg:grid-cols-[230px_1fr]">
        <aside className="border-b border-white/8 bg-[#091521] lg:border-r lg:border-b-0">
          <div className="flex items-center justify-between px-5 py-5 lg:block lg:px-6 lg:py-7">
            <div>
              <p className="text-[10px] font-semibold tracking-[0.28em] text-cyan-400">LOCAL AI DESK</p>
              <h1 className="mt-2 text-lg font-semibold tracking-tight">模拟交易驾驶舱</h1>
            </div>
            <div className="rounded-full border border-amber-400/30 bg-amber-300/10 px-3 py-1 text-[11px] font-medium text-amber-300">
              仅模拟交易 · 永不连接券商
            </div>
          </div>
          <nav className="flex gap-1 overflow-x-auto px-3 pb-4 lg:block lg:space-y-1 lg:px-3">
            {navigation.map((item) => (
              <button
                aria-label={item.label}
                className={`group flex min-w-fit items-center gap-3 rounded-md px-3 py-2.5 text-left text-sm transition lg:w-full ${
                  view === item.id
                    ? "bg-cyan-400/12 text-cyan-200"
                    : "text-slate-400 hover:bg-white/5 hover:text-slate-100"
                }`}
                key={item.id}
                onClick={() => onViewChange(item.id)}
                type="button"
              >
                <span className="font-mono text-[10px] text-slate-600 group-hover:text-cyan-500">
                  {item.code}
                </span>
                {item.label}
              </button>
            ))}
          </nav>
          <div className="hidden border-t border-white/8 px-6 py-5 lg:block">
            <p className="text-[10px] tracking-widest text-slate-600">风险模式 / AGGRESSIVE</p>
            <div className="mt-3 flex items-center justify-between text-xs">
              <span className="text-slate-500">最大回撤硬线</span>
              <span className="font-mono text-rose-300">30.00%</span>
            </div>
          </div>
        </aside>
        <div className="min-w-0">
          <header className="flex flex-wrap items-end justify-between gap-4 border-b border-white/8 px-5 py-4 md:px-8">
            <div>
              <p className="text-[10px] tracking-[0.2em] text-slate-500">COMBINED NAV / CNY</p>
              <p className="mt-1 font-mono text-2xl font-semibold tabular-nums">
                {account ? formatMicros(account.navMicros) : "--"}
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span
                className={`h-2 w-2 rounded-full ${unavailableCount === 0 ? "bg-emerald-400" : "bg-amber-400"}`}
              />
              {unavailableCount === 0 ? "全部数据链路正常" : `${unavailableCount} 个区域降级`}
            </div>
          </header>
          <main className="px-5 py-6 md:px-8 md:py-8">{children}</main>
        </div>
      </div>
    </div>
  );
}
