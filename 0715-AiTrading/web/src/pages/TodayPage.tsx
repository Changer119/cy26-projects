import { formatBps } from "../format";
import type { AccountSnapshot, PlanItem } from "../types";
import { BodyCell, DataTable, HeadCell, TableHead } from "../components/Table";
import { ActionPill, EmptyState, SectionHeader, StatCard } from "../components/Ui";

interface TodayPageProps {
  readonly account: AccountSnapshot | null;
  readonly plans: readonly PlanItem[];
}

export function TodayPage({ account, plans }: TodayPageProps) {
  const buyCount = plans.filter((plan) => plan.action === "BUY").length;
  const sellCount = plans.filter((plan) => plan.action === "SELL").length;
  return (
    <section>
      <SectionHeader
        aside={
          <div className="rounded border border-cyan-400/20 bg-cyan-400/5 px-3 py-2 font-mono text-xs text-cyan-300">
            PRE-MARKET 07:50 / POST-MARKET 18:15
          </div>
        }
        description="AGGRESSIVE_V2：DeepSeek仅给方向/置信度/理由，本地规则计算限价、止损和仓位"
        eyebrow="DAILY DECISION"
        title="今日交易计划"
      />
      <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard detail="含 HOLD，风险检查后冻结" label="计划标的" value={String(plans.length)} />
        <StatCard detail="新增风险暴露" label="拟买入" tone="positive" value={String(buyCount)} />
        <StatCard detail="降低组合风险" label="拟卖出" tone="negative" value={String(sellCount)} />
        <StatCard
          detail="硬线 30.00%"
          label="当前最大回撤"
          tone={(account?.maxDrawdownBps ?? 0) >= 2500 ? "warning" : "neutral"}
          value={account ? formatBps(account.maxDrawdownBps) : "--"}
        />
      </div>
      {plans.length === 0 ? (
        <EmptyState>今日尚无已生成计划；系统不会因为任务迟到而追单。</EmptyState>
      ) : (
        <DataTable>
          <TableHead>
            <HeadCell>标的</HeadCell>
            <HeadCell>动作</HeadCell>
            <HeadCell>置信度</HeadCell>
            <HeadCell>目标权重</HeadCell>
            <HeadCell>状态</HeadCell>
            <HeadCell>决策摘要</HeadCell>
          </TableHead>
          <tbody>
            {plans.map((plan) => (
              <tr key={`${plan.symbol}-${plan.status}`}>
                <BodyCell>
                  <span className="font-mono text-slate-100">{plan.symbol}</span>
                </BodyCell>
                <BodyCell>
                  <ActionPill action={plan.action} />
                </BodyCell>
                <BodyCell>{(plan.confidenceBps / 100).toFixed(0)}%</BodyCell>
                <BodyCell>{(plan.targetWeightBps / 100).toFixed(2)}%</BodyCell>
                <BodyCell>
                  <span className="font-mono text-xs text-cyan-300">{plan.status}</span>
                </BodyCell>
                <BodyCell>{plan.reason}</BodyCell>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
    </section>
  );
}
