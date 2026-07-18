import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import App from "../App";
import type { DashboardData } from "../types";

const dashboardData: DashboardData = {
  account: {
    initialCashMicros: 100_000_000_000,
    cashMicros: 72_000_000_000,
    marketValueMicros: 31_500_000_000,
    navMicros: 103_500_000_000,
    pnlMicros: 3_500_000_000,
    returnBps: 350,
    maxDrawdownBps: 620,
    updatedAt: "2026-07-15T18:15:00+08:00",
  },
  watchlist: [
    {
      symbol: "603005.SH",
      name: "晶方科技",
      market: "SSE",
      lastPriceMicros: 32_600_000,
      changeBps: 245,
      decision: "BUY",
      dataStatus: "healthy",
      addedBy: "USER",
    },
  ],
  orders: [
    {
      id: "order-1",
      symbol: "603005.SH",
      side: "BUY",
      quantity: 100,
      limitPriceMicros: 32_600_000,
      status: "FILLED",
      tradeDate: "2026-07-15",
      reason: "动量与成交量确认",
    },
  ],
  plans: [
    {
      symbol: "603005.SH",
      action: "BUY",
      confidenceBps: 7200,
      targetWeightBps: 1800,
      reason: "动量与成交量确认",
      status: "FROZEN",
    },
  ],
  performance: [
    {
      date: "2026-07-15",
      navMicros: 103_500_000_000,
      returnBps: 350,
      drawdownBps: 0,
    },
  ],
  dataHealth: [
    {
      provider: "Yahoo Finance",
      status: "healthy",
      latencyMs: 420,
      lastSuccessAt: "2026-07-15T18:15:00+08:00",
      message: "主行情可用",
    },
  ],
  unavailableSections: [],
};

describe("本地模拟交易仪表盘", () => {
  it("明确模拟交易属性并可切换六个高信息密度视图", async () => {
    const user = userEvent.setup();
    render(<App loader={async () => dashboardData} />);

    expect(await screen.findByText("今日交易计划")).toBeInTheDocument();
    expect(
      screen.getByText(
        "AGGRESSIVE_V2：DeepSeek仅给方向/置信度/理由，本地规则计算限价、止损和仓位",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("仅模拟交易 · 永不连接券商")).toBeInTheDocument();
    expect(screen.getByText("¥103,500.00")).toBeInTheDocument();

    const destinations = [
      ["组合", "组合风险与敞口"],
      ["自选股", "AI 与人工自选池"],
      ["交易日志", "模拟交易日志"],
      ["绩效", "收益与回撤"],
      ["数据健康", "行情与模型链路"],
      ["今日", "今日交易计划"],
    ] as const;
    for (const [buttonName, heading] of destinations) {
      await user.click(screen.getByRole("button", { name: buttonName }));
      expect(screen.getByText(heading)).toBeInTheDocument();
    }
  });
});
