import { describe, expect, it } from "vitest";

import { formatBps, formatMicros } from "../format";

describe("交易数值格式化", () => {
  it("把微单位金额格式化为人民币", () => {
    expect(formatMicros(103_500_000_000)).toBe("¥103,500.00");
  });

  it("为正负基点添加方向符号", () => {
    expect(formatBps(350)).toBe("+3.50%");
    expect(formatBps(-125)).toBe("-1.25%");
    expect(formatBps(0)).toBe("0.00%");
  });
});
