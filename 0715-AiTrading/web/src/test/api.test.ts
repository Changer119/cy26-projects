import { describe, expect, it } from "vitest";

import { ApiContractError, parseAccount } from "../api";

describe("账户 API 类型解析", () => {
  it("把符合契约的未知响应解析为强类型账户快照", () => {
    const payload: unknown = {
      initial_cash_micros: 100_000_000_000,
      cash_micros: 72_000_000_000,
      market_value_micros: 31_500_000_000,
      nav_micros: 103_500_000_000,
      pnl_micros: 3_500_000_000,
      return_bps: 350,
      max_drawdown_bps: 620,
      updated_at: "2026-07-15T18:15:00+08:00",
    };

    const account = parseAccount(payload);

    expect(account.navMicros).toBe(103_500_000_000);
    expect(account.returnBps).toBe(350);
    expect(account.updatedAt).toBe("2026-07-15T18:15:00+08:00");
  });

  it("拒绝缺字段或字段类型错误的响应", () => {
    const payload: unknown = { nav_micros: "103500" };

    expect(() => parseAccount(payload)).toThrow(ApiContractError);
  });
});
