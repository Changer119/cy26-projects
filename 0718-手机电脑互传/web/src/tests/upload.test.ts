import { describe, expect, it } from "vitest";

import { TransferQueue, type UploadCallbacks, type UploadRunner } from "../upload";

describe("TransferQueue", () => {
  it("最多同时运行三个上传并在完成后启动下一个", () => {
    const started: Array<{ file: File; callbacks: UploadCallbacks }> = [];
    const runner: UploadRunner = (file, callbacks) => {
      started.push({ file, callbacks });
      return { abort: async () => undefined };
    };
    const queue = new TransferQueue(runner, 3);
    const files = ["1.jpg", "2.jpg", "3.jpg", "4.jpg"].map(
      (name) => new File([name], name, { type: "image/jpeg" }),
    );

    queue.add(files);
    queue.start();

    expect(started.map(({ file }) => file.name)).toEqual(["1.jpg", "2.jpg", "3.jpg"]);
    started[0].callbacks.onSuccess();
    expect(started.map(({ file }) => file.name)).toEqual([
      "1.jpg",
      "2.jpg",
      "3.jpg",
      "4.jpg",
    ]);
  });

  it("在进度变化时发布不可变快照", () => {
    let callbacks: UploadCallbacks | undefined;
    const snapshots: Array<ReadonlyArray<{ state: string; uploadedBytes: number }>> = [];
    const runner: UploadRunner = (_file, nextCallbacks) => {
      callbacks = nextCallbacks;
      return { abort: async () => undefined };
    };
    const queue = new TransferQueue(runner, 1, (items) => {
      snapshots.push(items.map(({ state, uploadedBytes }) => ({ state, uploadedBytes })));
    });

    queue.add([new File(["1234"], "IMG.jpg", { type: "image/jpeg" })]);
    queue.start();
    callbacks?.onProgress(2, 4);

    expect(snapshots.at(-1)).toEqual([{ state: "uploading", uploadedBytes: 2 }]);
  });

  it("可以暂停并继续整个队列", async () => {
    let starts = 0;
    let aborts = 0;
    let latestStates: string[] = [];
    const runner: UploadRunner = () => {
      starts += 1;
      return {
        abort: async () => {
          aborts += 1;
        },
      };
    };
    const queue = new TransferQueue(runner, 1, (items) => {
      latestStates = items.map(({ state }) => state);
    });
    queue.add([new File(["1"], "1.jpg"), new File(["2"], "2.jpg")]);
    queue.start();

    await queue.pauseAll();
    expect(aborts).toBe(1);
    expect(latestStates).toEqual(["paused", "paused"]);

    queue.resumeAll();
    expect(starts).toBe(2);
    expect(latestStates).toEqual(["uploading", "waiting"]);
  });

  it("可以重新上传失败文件", () => {
    const callbacks: UploadCallbacks[] = [];
    let latestState = "";
    const runner: UploadRunner = (_file, nextCallbacks) => {
      callbacks.push(nextCallbacks);
      return { abort: async () => undefined };
    };
    const queue = new TransferQueue(runner, 1, (items) => {
      latestState = items[0]?.state ?? "";
    });
    queue.add([new File(["x"], "failed.jpg")]);
    queue.start();
    callbacks[0].onError(new Error("Wi-Fi 中断"));

    expect(latestState).toBe("failed");
    queue.retryFailed();

    expect(callbacks).toHaveLength(2);
    expect(latestState).toBe("uploading");
  });
});
