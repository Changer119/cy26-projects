export type Market = "SSE" | "SZSE" | "HKEX";
export type TradeAction = "BUY" | "SELL" | "HOLD";
export type OrderStatus =
  | "PENDING_OPEN"
  | "FILLED"
  | "UNFILLED"
  | "EXECUTION_REJECTED"
  | "DATA_UNAVAILABLE";
export type HealthStatus = "healthy" | "degraded" | "unavailable";

export interface AccountSnapshot {
  readonly initialCashMicros: number;
  readonly cashMicros: number;
  readonly marketValueMicros: number;
  readonly navMicros: number;
  readonly pnlMicros: number;
  readonly returnBps: number;
  readonly maxDrawdownBps: number;
  readonly updatedAt: string;
}

export interface WatchlistItem {
  readonly symbol: string;
  readonly name: string;
  readonly market: Market;
  readonly lastPriceMicros: number | null;
  readonly changeBps: number | null;
  readonly decision: TradeAction;
  readonly dataStatus: HealthStatus;
  readonly addedBy: "USER" | "AI";
}

export interface OrderItem {
  readonly id: string;
  readonly symbol: string;
  readonly side: "BUY" | "SELL";
  readonly quantity: number;
  readonly limitPriceMicros: number;
  readonly status: OrderStatus;
  readonly tradeDate: string;
  readonly reason: string;
}

export interface PlanItem {
  readonly symbol: string;
  readonly action: TradeAction;
  readonly confidenceBps: number;
  readonly targetWeightBps: number;
  readonly reason: string;
  readonly status: "DRAFT" | "RISK_CHECKED" | "FROZEN" | "RECONCILED" | "ABORTED";
}

export interface PerformancePoint {
  readonly date: string;
  readonly navMicros: number;
  readonly returnBps: number;
  readonly drawdownBps: number;
}

export interface DataHealthItem {
  readonly provider: string;
  readonly status: HealthStatus;
  readonly latencyMs: number | null;
  readonly lastSuccessAt: string | null;
  readonly message: string;
}

export interface DashboardData {
  readonly account: AccountSnapshot | null;
  readonly watchlist: readonly WatchlistItem[];
  readonly orders: readonly OrderItem[];
  readonly plans: readonly PlanItem[];
  readonly performance: readonly PerformancePoint[];
  readonly dataHealth: readonly DataHealthItem[];
  readonly unavailableSections: readonly string[];
}
