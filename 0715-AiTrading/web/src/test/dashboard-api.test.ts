import { describe, expect, it } from "vitest";

import { loadDashboardData } from "../api";

const accountPayload: unknown = {
  initial_cash_micros: 100_000_000_000,
  cash_micros: 72_000_000_000,
  market_value_micros: 31_500_000_000,
  nav_micros: 103_500_000_000,
  pnl_micros: 3_500_000_000,
  return_bps: 350,
  max_drawdown_bps: 620,
  updated_at: "2026-07-15T18:15:00+08:00",
};

function apiResponse(path: string): Response {
  switch (path) {
    case "/api/account":
      return Response.json(accountPayload);
    case "/api/watchlist":
      return Response.json({
        items: [
          {
            symbol: "603005.SH",
            name: "晶方科技",
            market: "SSE",
            last_price_micros: 32_600_000,
            change_bps: 245,
            decision: "BUY",
            data_status: "healthy",
            added_by: "USER",
          },
        ],
      });
    case "/api/orders":
      return Response.json({
        items: [
          {
            id: "order-1",
            symbol: "603005.SH",
            side: "BUY",
            quantity: 100,
            limit_price_micros: 32_600_000,
            status: "PENDING_OPEN",
            trade_date: "2026-07-15",
            reason: "动量与成交量确认",
          },
        ],
      });
    case "/api/plans":
      return Response.json({
        items: [
          {
            symbol: "603005.SH",
            action: "BUY",
            confidence_bps: 7200,
            target_weight_bps: 1800,
            reason: "动量与成交量确认",
            status: "FROZEN",
          },
        ],
      });
    case "/api/performance":
      return Response.json({
        points: [
          {
            date: "2026-07-15",
            nav_micros: 103_500_000_000,
            return_bps: 350,
            drawdown_bps: 0,
          },
        ],
      });
    case "/api/data-health":
      return Response.json({
        items: [
          {
            provider: "Yahoo Finance",
            status: "healthy",
            latency_ms: 420,
            last_success_at: "2026-07-15T18:15:00+08:00",
            message: "主行情可用",
          },
        ],
      });
    default:
      return new Response(null, { status: 404 });
  }
}

const transport: typeof fetch = async (input) => {
  const url = input instanceof Request ? input.url : String(input);
  return apiResponse(new URL(url, "http://localhost").pathname);
};

describe("仪表盘 API 聚合", () => {
  it("并行加载并解析六类只读数据", async () => {
    const data = await loadDashboardData(transport);

    expect(data.account?.navMicros).toBe(103_500_000_000);
    expect(data.watchlist[0]?.name).toBe("晶方科技");
    expect(data.orders[0]?.status).toBe("PENDING_OPEN");
    expect(data.plans[0]?.action).toBe("BUY");
    expect(data.performance).toHaveLength(1);
    expect(data.dataHealth[0]?.provider).toBe("Yahoo Finance");
    expect(data.unavailableSections).toEqual([]);
  });

  it("单个接口失败时保留其他区域并标记降级", async () => {
    const degradedTransport: typeof fetch = async (input) => {
      const url = input instanceof Request ? input.url : String(input);
      const path = new URL(url, "http://localhost").pathname;
      return path === "/api/performance"
        ? new Response(null, { status: 503 })
        : apiResponse(path);
    };

    const data = await loadDashboardData(degradedTransport);

    expect(data.account).not.toBeNull();
    expect(data.performance).toEqual([]);
    expect(data.unavailableSections).toEqual(["绩效"]);
  });
});
