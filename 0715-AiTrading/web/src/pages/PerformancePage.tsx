import { PerformanceChart } from "../components/PerformanceChart";
import { SectionHeader, StatCard } from "../components/Ui";
import { formatBps, formatMicros } from "../format";
import type { AccountSnapshot, PerformancePoint } from "../types";

interface PerformancePageProps {
  readonly account: AccountSnapshot | null;
  readonly points: readonly PerformancePoint[];
}

export function PerformancePage({ account, points }: PerformancePageProps) {
  const latest = points.at(-1);
  return (
    <section>
      <SectionHeader
        description="收盘后按最新可用价格重估，追踪绝对收益、累计收益和最大回撤。"
        eyebrow="PERFORMANCE"
        title="收益与回撤"
      />
      <div className="mb-6 grid gap-3 sm:grid-cols-3">
        <StatCard
          detail={latest ? `截至 ${latest.date}` : "等待首次收盘"}
          label="最新净值"
          value={latest ? formatMicros(latest.navMicros) : "--"}
        />
        <StatCard
          detail="基于初始 10 万元"
          label="累计收益"
          tone={(account?.returnBps ?? 0) >= 0 ? "positive" : "negative"}
          value={account ? formatBps(account.returnBps) : "--"}
        />
        <StatCard
          detail="30% 触发硬线"
          label="最大回撤"
          tone={(account?.maxDrawdownBps ?? 0) >= 2000 ? "warning" : "neutral"}
          value={account ? formatBps(account.maxDrawdownBps) : "--"}
        />
      </div>
      <PerformanceChart points={points} />
    </section>
  );
}
