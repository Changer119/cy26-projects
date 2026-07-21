import {
  parseAccount,
  parseDataHealth,
  parseOrders,
  parsePerformance,
  parsePlans,
  parseWatchlist,
} from "./decoders";
import type { DashboardData } from "./types";

export { ApiContractError, parseAccount } from "./decoders";

interface SectionResult<T> {
  readonly available: boolean;
  readonly value: T;
}

async function fetchPayload(path: string, transport: typeof fetch): Promise<unknown> {
  const response = await transport(path, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`${path} 返回 HTTP ${response.status}`);
  return JSON.parse(await response.text()) as unknown;
}

async function loadSection<T>(
  path: string,
  fallback: T,
  decoder: (payload: unknown) => T,
  transport: typeof fetch,
): Promise<SectionResult<T>> {
  try {
    const payload = await fetchPayload(path, transport);
    return { available: true, value: decoder(payload) };
  } catch {
    return { available: false, value: fallback };
  }
}

export async function loadDashboardData(transport: typeof fetch = fetch): Promise<DashboardData> {
  const [account, watchlist, orders, plans, performance, dataHealth] = await Promise.all([
    loadSection("/api/account", null, parseAccount, transport),
    loadSection("/api/watchlist", [], parseWatchlist, transport),
    loadSection("/api/orders", [], parseOrders, transport),
    loadSection("/api/plans", [], parsePlans, transport),
    loadSection("/api/performance", [], parsePerformance, transport),
    loadSection("/api/data-health", [], parseDataHealth, transport),
  ]);
  const unavailableSections: string[] = [];
  if (!account.available) unavailableSections.push("组合");
  if (!watchlist.available) unavailableSections.push("自选股");
  if (!orders.available) unavailableSections.push("交易日志");
  if (!plans.available) unavailableSections.push("今日");
  if (!performance.available) unavailableSections.push("绩效");
  if (!dataHealth.available) unavailableSections.push("数据健康");
  return {
    account: account.value,
    watchlist: watchlist.value,
    orders: orders.value,
    plans: plans.value,
    performance: performance.value,
    dataHealth: dataHealth.value,
    unavailableSections,
  };
}
