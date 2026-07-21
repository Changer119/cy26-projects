import type {
  AccountSnapshot,
  DataHealthItem,
  HealthStatus,
  Market,
  OrderItem,
  OrderStatus,
  PerformancePoint,
  PlanItem,
  TradeAction,
  WatchlistItem,
} from "./types";

export class ApiContractError extends Error {
  public constructor(message: string) {
    super(message);
    this.name = "ApiContractError";
  }
}

function requireObject(value: unknown): object {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new ApiContractError("API 响应必须是对象");
  }
  return value;
}

function requiredNumber(source: object, key: string): number {
  const value: unknown = Reflect.get(source, key);
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new ApiContractError(`字段 ${key} 必须是有限数字`);
  }
  return value;
}

function nullableNumber(source: object, key: string): number | null {
  const value: unknown = Reflect.get(source, key);
  if (value === null) return null;
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new ApiContractError(`字段 ${key} 必须是有限数字或 null`);
  }
  return value;
}

function requiredString(source: object, key: string): string {
  const value: unknown = Reflect.get(source, key);
  if (typeof value !== "string" || value.length === 0) {
    throw new ApiContractError(`字段 ${key} 必须是非空字符串`);
  }
  return value;
}

function nullableString(source: object, key: string): string | null {
  const value: unknown = Reflect.get(source, key);
  if (value === null) return null;
  if (typeof value !== "string" || value.length === 0) {
    throw new ApiContractError(`字段 ${key} 必须是非空字符串或 null`);
  }
  return value;
}

function requiredEnum<T extends string>(source: object, key: string, allowed: readonly T[]): T {
  const value = requiredString(source, key);
  const match = allowed.find((candidate) => candidate === value);
  if (match === undefined) throw new ApiContractError(`字段 ${key} 的枚举值无效`);
  return match;
}

function requiredArray(payload: unknown, key: string): readonly unknown[] {
  const source = requireObject(payload);
  const value: unknown = Reflect.get(source, key);
  if (!Array.isArray(value)) throw new ApiContractError(`字段 ${key} 必须是数组`);
  return value;
}

export function parseAccount(payload: unknown): AccountSnapshot {
  const source = requireObject(payload);
  return {
    initialCashMicros: requiredNumber(source, "initial_cash_micros"),
    cashMicros: requiredNumber(source, "cash_micros"),
    marketValueMicros: requiredNumber(source, "market_value_micros"),
    navMicros: requiredNumber(source, "nav_micros"),
    pnlMicros: requiredNumber(source, "pnl_micros"),
    returnBps: requiredNumber(source, "return_bps"),
    maxDrawdownBps: requiredNumber(source, "max_drawdown_bps"),
    updatedAt: requiredString(source, "updated_at"),
  };
}

export function parseWatchlist(payload: unknown): readonly WatchlistItem[] {
  return requiredArray(payload, "items").map((value) => {
    const source = requireObject(value);
    return {
      symbol: requiredString(source, "symbol"),
      name: requiredString(source, "name"),
      market: requiredEnum<Market>(source, "market", ["SSE", "SZSE", "HKEX"]),
      lastPriceMicros: nullableNumber(source, "last_price_micros"),
      changeBps: nullableNumber(source, "change_bps"),
      decision: requiredEnum<TradeAction>(source, "decision", ["BUY", "SELL", "HOLD"]),
      dataStatus: requiredEnum<HealthStatus>(source, "data_status", [
        "healthy",
        "degraded",
        "unavailable",
      ]),
      addedBy: requiredEnum<"USER" | "AI">(source, "added_by", ["USER", "AI"]),
    };
  });
}

export function parseOrders(payload: unknown): readonly OrderItem[] {
  return requiredArray(payload, "items").map((value) => {
    const source = requireObject(value);
    return {
      id: requiredString(source, "id"),
      symbol: requiredString(source, "symbol"),
      side: requiredEnum<"BUY" | "SELL">(source, "side", ["BUY", "SELL"]),
      quantity: requiredNumber(source, "quantity"),
      limitPriceMicros: requiredNumber(source, "limit_price_micros"),
      status: requiredEnum<OrderStatus>(source, "status", [
        "PENDING_OPEN",
        "FILLED",
        "UNFILLED",
        "EXECUTION_REJECTED",
        "DATA_UNAVAILABLE",
      ]),
      tradeDate: requiredString(source, "trade_date"),
      reason: requiredString(source, "reason"),
    };
  });
}

export function parsePlans(payload: unknown): readonly PlanItem[] {
  return requiredArray(payload, "items").map((value) => {
    const source = requireObject(value);
    return {
      symbol: requiredString(source, "symbol"),
      action: requiredEnum<TradeAction>(source, "action", ["BUY", "SELL", "HOLD"]),
      confidenceBps: requiredNumber(source, "confidence_bps"),
      targetWeightBps: requiredNumber(source, "target_weight_bps"),
      reason: requiredString(source, "reason"),
      status: requiredEnum<PlanItem["status"]>(source, "status", [
        "DRAFT",
        "RISK_CHECKED",
        "FROZEN",
        "RECONCILED",
        "ABORTED",
      ]),
    };
  });
}

export function parsePerformance(payload: unknown): readonly PerformancePoint[] {
  return requiredArray(payload, "points").map((value) => {
    const source = requireObject(value);
    return {
      date: requiredString(source, "date"),
      navMicros: requiredNumber(source, "nav_micros"),
      returnBps: requiredNumber(source, "return_bps"),
      drawdownBps: requiredNumber(source, "drawdown_bps"),
    };
  });
}

export function parseDataHealth(payload: unknown): readonly DataHealthItem[] {
  return requiredArray(payload, "items").map((value) => {
    const source = requireObject(value);
    return {
      provider: requiredString(source, "provider"),
      status: requiredEnum<HealthStatus>(source, "status", [
        "healthy",
        "degraded",
        "unavailable",
      ]),
      latencyMs: nullableNumber(source, "latency_ms"),
      lastSuccessAt: nullableString(source, "last_success_at"),
      message: requiredString(source, "message"),
    };
  });
}
