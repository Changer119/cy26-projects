import { formatBps, formatMicros } from "../format";
import type { AccountSnapshot } from "../types";
import { EmptyState, SectionHeader, StatCard } from "../components/Ui";

export function PortfolioPage({ account }: { readonly account: AccountSnapshot | null }) {
  if (account === null) {
    return (
      <section>
        <SectionHeader description="账户读模型暂不可用。" eyebrow="PORTFOLIO" title="组合风险与敞口" />
        <EmptyState>账户尚未初始化或 API 暂不可用。</EmptyState>
      </section>
    );
  }
  const cashWeight = account.navMicros === 0 ? 0 : (account.cashMicros / account.navMicros) * 100;
  const investedWeight = account.navMicros === 0 ? 0 : (account.marketValueMicros / account.navMicros) * 100;
  return (
    <section>
      <SectionHeader
        description="A 股、场内基金与港股账户统一折算为人民币组合净值。"
        eyebrow="PORTFOLIO"
        title="组合风险与敞口"
      />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard detail={`初始 ${formatMicros(account.initialCashMicros)}`} label="组合净值" value={formatMicros(account.navMicros)} />
        <StatCard detail={`${cashWeight.toFixed(1)}% 现金权重`} label="可用现金" value={formatMicros(account.cashMicros)} />
        <StatCard detail={`${investedWeight.toFixed(1)}% 已投资`} label="证券市值" value={formatMicros(account.marketValueMicros)} />
        <StatCard
          detail={`累计收益 ${formatBps(account.returnBps)}`}
          label="累计盈亏"
          tone={account.pnlMicros >= 0 ? "positive" : "negative"}
          value={formatMicros(account.pnlMicros)}
        />
      </div>
      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        <article className="rounded-lg border border-white/8 bg-white/[0.02] p-5">
          <h3 className="text-sm font-medium">资金结构</h3>
          <div className="mt-5 h-3 overflow-hidden rounded-full bg-white/5">
            <div className="h-full bg-cyan-400" style={{ width: `${Math.min(investedWeight, 100)}%` }} />
          </div>
          <div className="mt-4 flex justify-between text-xs text-slate-400">
            <span>证券 {investedWeight.toFixed(1)}%</span>
            <span>现金 {cashWeight.toFixed(1)}%</span>
          </div>
        </article>
        <article className="rounded-lg border border-white/8 bg-white/[0.02] p-5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium">回撤预算</h3>
            <span className="font-mono text-xs text-rose-300">硬线 30.00%</span>
          </div>
          <div className="mt-5 h-3 overflow-hidden rounded-full bg-white/5">
            <div
              className="h-full bg-amber-400"
              style={{ width: `${Math.min(account.maxDrawdownBps / 30, 100)}%` }}
            />
          </div>
          <p className="mt-4 text-xs text-slate-400">已使用 {formatBps(account.maxDrawdownBps)} 的回撤空间</p>
        </article>
      </div>
    </section>
  );
}
