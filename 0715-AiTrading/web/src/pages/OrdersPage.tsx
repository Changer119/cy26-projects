import type { OrderItem } from "../types";
import { BodyCell, DataTable, HeadCell, TableHead } from "../components/Table";
import { EmptyState, SectionHeader } from "../components/Ui";

export function OrdersPage({ orders }: { readonly orders: readonly OrderItem[] }) {
  return (
    <section>
      <SectionHeader
        description="所有订单均为本地账本中的模拟动作；未成交订单同样占用当日标的操作额度。"
        eyebrow="PAPER LEDGER"
        title="模拟交易日志"
      />
      {orders.length === 0 ? (
        <EmptyState>尚无模拟订单。</EmptyState>
      ) : (
        <DataTable>
          <TableHead>
            <HeadCell>日期 / ID</HeadCell>
            <HeadCell>标的</HeadCell>
            <HeadCell>方向</HeadCell>
            <HeadCell>数量</HeadCell>
            <HeadCell>限价</HeadCell>
            <HeadCell>结果</HeadCell>
            <HeadCell>原因</HeadCell>
          </TableHead>
          <tbody>
            {orders.map((order) => (
              <tr key={order.id}>
                <BodyCell>
                  <p>{order.tradeDate}</p>
                  <p className="mt-1 font-mono text-[10px] text-slate-600">{order.id}</p>
                </BodyCell>
                <BodyCell>
                  <span className="font-mono text-slate-100">{order.symbol}</span>
                </BodyCell>
                <BodyCell>
                  <span className={order.side === "BUY" ? "text-emerald-300" : "text-rose-300"}>{order.side}</span>
                </BodyCell>
                <BodyCell>{order.quantity.toLocaleString("zh-CN")}</BodyCell>
                <BodyCell>¥{(order.limitPriceMicros / 1_000_000).toFixed(2)}</BodyCell>
                <BodyCell>
                  <span className="font-mono text-xs text-cyan-300">{order.status}</span>
                </BodyCell>
                <BodyCell>{order.reason}</BodyCell>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
    </section>
  );
}
