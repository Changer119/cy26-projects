import type { WatchlistItem } from "../types";
import { BodyCell, DataTable, HeadCell, TableHead } from "../components/Table";
import { ActionPill, EmptyState, HealthPill, SectionHeader } from "../components/Ui";

export function WatchlistPage({ items }: { readonly items: readonly WatchlistItem[] }) {
  return (
    <section>
      <SectionHeader
        aside={<span className="font-mono text-xs text-slate-400">{items.length} SYMBOLS</span>}
        description="系统可发现科创板、创业板和港股机会；AI 新增标的会同步发送飞书通知。"
        eyebrow="UNIVERSE"
        title="AI 与人工自选池"
      />
      {items.length === 0 ? (
        <EmptyState>自选池为空或行情接口暂不可用。</EmptyState>
      ) : (
        <DataTable>
          <TableHead>
            <HeadCell>证券</HeadCell>
            <HeadCell>市场</HeadCell>
            <HeadCell>最新价</HeadCell>
            <HeadCell>日涨跌</HeadCell>
            <HeadCell>AI 判断</HeadCell>
            <HeadCell>数据</HeadCell>
            <HeadCell>来源</HeadCell>
          </TableHead>
          <tbody>
            {items.map((item) => (
              <tr key={item.symbol}>
                <BodyCell>
                  <p className="font-medium text-slate-100">{item.name}</p>
                  <p className="mt-1 font-mono text-xs text-slate-500">{item.symbol}</p>
                </BodyCell>
                <BodyCell>{item.market}</BodyCell>
                <BodyCell>
                  <span className="font-mono tabular-nums">
                    {item.lastPriceMicros === null
                      ? "--"
                      : `${item.market === "HKEX" ? "HK$" : "¥"}${(item.lastPriceMicros / 1_000_000).toFixed(2)}`}
                  </span>
                </BodyCell>
                <BodyCell>
                  <span className={item.changeBps !== null && item.changeBps < 0 ? "text-rose-300" : "text-emerald-300"}>
                    {item.changeBps === null ? "--" : `${item.changeBps > 0 ? "+" : ""}${(item.changeBps / 100).toFixed(2)}%`}
                  </span>
                </BodyCell>
                <BodyCell>
                  <ActionPill action={item.decision} />
                </BodyCell>
                <BodyCell>
                  <HealthPill status={item.dataStatus} />
                </BodyCell>
                <BodyCell>{item.addedBy === "AI" ? "AI 发现" : "人工"}</BodyCell>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
    </section>
  );
}
