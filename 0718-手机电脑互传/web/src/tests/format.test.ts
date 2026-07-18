import { expect, it } from "vitest";

import { formatBytes } from "../format";

it("以适合传输界面的单位格式化字节数", () => {
  expect(formatBytes(0)).toBe("0 B");
  expect(formatBytes(1_536)).toBe("1.5 KB");
  expect(formatBytes(2 * 1024 * 1024 * 1024)).toBe("2 GB");
});
