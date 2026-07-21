import { expect, it, vi } from "vitest";

import { consumePairingToken, loadAdminConfig } from "../api";

it("保存二维码令牌并立即从地址栏移除", () => {
  const storage = new Map<string, string>();
  const sessionStorageLike = {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => storage.set(key, value),
  };
  const replaceState = vi.fn();

  const token = consumePairingToken(
    new URL("http://192.168.1.20:8765/?token=secret-token"),
    sessionStorageLike,
    replaceState,
  );

  expect(token).toBe("secret-token");
  expect(storage.get("phone2computer-token")).toBe("secret-token");
  expect(replaceState).toHaveBeenCalledWith(null, "", "/");
});

it("地址中没有令牌时读取会话中的已有令牌", () => {
  const storage = {
    getItem: () => "saved-token",
    setItem: vi.fn(),
  };

  expect(consumePairingToken(new URL("http://localhost/"), storage, vi.fn())).toBe("saved-token");
});

it("从本机管理接口读取二维码配置", async () => {
  const fetcher = vi.fn(async () => new Response(JSON.stringify({
    upload_url: "http://192.168.1.20:8765/?token=abc",
    output_directory: "/tmp/Phone2Computer",
  }), { status: 200 }));

  const config = await loadAdminConfig(fetcher);

  expect(fetcher).toHaveBeenCalledWith("/api/admin/config");
  expect(config.output_directory).toBe("/tmp/Phone2Computer");
});
