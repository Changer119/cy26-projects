import * as tus from "tus-js-client";

export type TransferState = "waiting" | "uploading" | "paused" | "success" | "failed";

export interface TransferItem {
  id: string;
  file: File;
  state: TransferState;
  uploadedBytes: number;
  totalBytes: number;
  errorMessage?: string;
}

export interface UploadCallbacks {
  onProgress: (uploadedBytes: number, totalBytes: number) => void;
  onSuccess: () => void;
  onError: (error: Error) => void;
}

export interface UploadControl {
  abort: () => Promise<void>;
}

export type UploadRunner = (file: File, callbacks: UploadCallbacks) => UploadControl;

export function createTusRunner(token: string): UploadRunner {
  return (file, callbacks) => {
    const upload = new tus.Upload(file, {
      endpoint: "/api/files/",
      chunkSize: 8 * 1024 * 1024,
      retryDelays: [0, 1_000, 3_000, 5_000],
      headers: { Authorization: `Bearer ${token}` },
      metadata: {
        filename: file.name,
        filetype: file.type,
        lastmodified: String(file.lastModified),
      },
      onProgress: callbacks.onProgress,
      onSuccess: callbacks.onSuccess,
      onError: callbacks.onError,
    });
    upload.start();
    return {
      abort: () => upload.abort(true),
    };
  };
}

export class TransferQueue {
  private readonly items: TransferItem[] = [];
  private readonly active = new Map<string, UploadControl>();
  private nextID = 1;

  constructor(
    private readonly runner: UploadRunner,
    private readonly concurrency: number,
    private readonly onChange: (items: ReadonlyArray<TransferItem>) => void = () => undefined,
  ) {}

  add(files: File[]): void {
    for (const file of files) {
      this.items.push({
        id: String(this.nextID++),
        file,
        state: "waiting",
        uploadedBytes: 0,
        totalBytes: file.size,
      });
    }
    this.publish();
  }

  start(): void {
    this.pump();
  }

  async pauseAll(): Promise<void> {
    const controls = Array.from(this.active.values());
    this.active.clear();
    for (const item of this.items) {
      if (item.state === "waiting" || item.state === "uploading") {
        item.state = "paused";
      }
    }
    await Promise.all(controls.map(({ abort }) => abort()));
    this.publish();
  }

  resumeAll(): void {
    for (const item of this.items) {
      if (item.state === "paused") {
        item.state = "waiting";
      }
    }
    this.publish();
    this.pump();
  }

  retryFailed(): void {
    for (const item of this.items) {
      if (item.state === "failed") {
        item.state = "waiting";
        item.errorMessage = undefined;
      }
    }
    this.publish();
    this.pump();
  }

  private pump(): void {
    while (this.active.size < this.concurrency) {
      const item = this.items.find(({ state }) => state === "waiting");
      if (!item) return;
      item.state = "uploading";
      this.publish();
      const control = this.runner(item.file, {
        onProgress: (uploadedBytes, totalBytes) => {
          item.uploadedBytes = uploadedBytes;
          item.totalBytes = totalBytes;
          this.publish();
        },
        onSuccess: () => {
          item.state = "success";
          item.uploadedBytes = item.totalBytes;
          this.active.delete(item.id);
          this.publish();
          this.pump();
        },
        onError: (error) => {
          item.state = "failed";
          item.errorMessage = error.message;
          this.active.delete(item.id);
          this.publish();
          this.pump();
        },
      });
      this.active.set(item.id, control);
    }
  }

  private publish(): void {
    this.onChange(this.items.map((item) => ({ ...item })));
  }
}
