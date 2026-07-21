import type { DataHealthItem } from "../types";
import { EmptyState, HealthPill, SectionHeader } from "../components/Ui";

export function DataHealthPage({ items }: { readonly items: readonly DataHealthItem[] }) {
  return (
    <section>
      <SectionHeader
        description="免费公开行情、DeepSeek 决策和本地账本必须满足新鲜度要求；异常时系统默认不交易。"
        eyebrow="OBSERVABILITY"
        title="行情与模型链路"
      />
      {items.length === 0 ? (
        <EmptyState>暂无健康探针数据；交易引擎将按 fail-closed 处理。</EmptyState>
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {items.map((item) => (
            <article className="rounded-lg border border-white/8 bg-white/[0.02] p-5" key={item.provider}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-[10px] tracking-[0.18em] text-slate-500">PROVIDER</p>
                  <h3 className="mt-2 font-medium">{item.provider}</h3>
                </div>
                <HealthPill status={item.status} />
              </div>
              <div className="mt-5 grid grid-cols-2 gap-3 border-t border-white/6 pt-4 text-xs">
                <div>
                  <p className="text-slate-600">延迟</p>
                  <p className="mt-1 font-mono text-slate-300">{item.latencyMs === null ? "--" : `${item.latencyMs} ms`}</p>
                </div>
                <div>
                  <p className="text-slate-600">最近成功</p>
                  <p className="mt-1 truncate font-mono text-slate-300">{item.lastSuccessAt ?? "--"}</p>
                </div>
              </div>
              <p className="mt-4 text-xs leading-5 text-slate-400">{item.message}</p>
            </article>
          ))}
        </div>
      )}
      <div className="mt-6 rounded-lg border border-amber-400/15 bg-amber-400/5 px-4 py-3 text-xs text-amber-200/80">
        数据缺失、时间戳过期或模型响应不满足结构化契约时，不创建新订单。
      </div>
    </section>
  );
}
