import { expect, it, vi } from "vitest";

const tusState = vi.hoisted(() => ({
  options: undefined as TusOptions | undefined,
  start: vi.fn(),
  abort: vi.fn(async () => undefined),
}));

interface TusOptions {
  endpoint: string;
  chunkSize: number;
  headers: Record<string, string>;
  metadata: Record<string, string>;
  onProgress: (uploaded: number, total: number) => void;
  onSuccess: () => void;
  onError: (error: Error) => void;
}

vi.mock("tus-js-client", () => ({
  Upload: class {
    constructor(_file: File, options: TusOptions) {
      tusState.options = options;
    }

    start = tusState.start;
    abort = tusState.abort;
  },
}));

import { createTusRunner } from "../upload";

it("为 tus 上传配置认证、分片和媒体元数据", async () => {
  const callbacks = {
    onProgress: vi.fn(),
    onSuccess: vi.fn(),
    onError: vi.fn(),
  };
  const file = new File(["photo"], "IMG_001.jpg", {
    type: "image/jpeg",
    lastModified: 1_700_000_000_000,
  });

  const control = createTusRunner("session-token")(file, callbacks);

  expect(tusState.start).toHaveBeenCalledOnce();
  expect(tusState.options?.endpoint).toBe("/api/files/");
  expect(tusState.options?.chunkSize).toBe(8 * 1024 * 1024);
  expect(tusState.options?.headers.Authorization).toBe("Bearer session-token");
  expect(tusState.options?.metadata).toMatchObject({
    filename: "IMG_001.jpg",
    filetype: "image/jpeg",
    lastmodified: "1700000000000",
  });

  tusState.options?.onProgress(2, 5);
  expect(callbacks.onProgress).toHaveBeenCalledWith(2, 5);
  await control.abort();
  expect(tusState.abort).toHaveBeenCalledWith(true);
});
