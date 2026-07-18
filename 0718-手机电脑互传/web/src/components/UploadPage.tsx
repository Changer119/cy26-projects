import { useMemo, useState } from "react";

import { formatBytes } from "../format";
import { TransferQueue, type TransferItem, type UploadRunner } from "../upload";

interface UploadPageProps {
  runner: UploadRunner;
}

const stateLabels: Record<TransferItem["state"], string> = {
  waiting: "等待中",
  uploading: "传输中",
  paused: "已暂停",
  success: "已完成",
  failed: "失败",
};

export function UploadPage({ runner }: UploadPageProps) {
  const [items, setItems] = useState<ReadonlyArray<TransferItem>>([]);
  const queue = useMemo(() => new TransferQueue(runner, 3, setItems), [runner]);
  const totalBytes = items.reduce((sum, item) => sum + item.totalBytes, 0);
  const uploadedBytes = items.reduce((sum, item) => sum + item.uploadedBytes, 0);
  const completed = items.filter(({ state }) => state === "success").length;
  const failed = items.filter(({ state }) => state === "failed").length;
  const isPaused = items.some(({ state }) => state === "paused");
  const progress = totalBytes === 0 ? 0 : Math.round((uploadedBytes / totalBytes) * 100);

  const selectFiles = (fileList: FileList | null) => {
    if (!fileList?.length) return;
    queue.add(Array.from(fileList));
    queue.start();
  };

  return (
    <main className="upload-shell">
      <header className="mobile-header">
        <div className="brand-mark small">P2C</div>
        <div className="connection-pill"><span />已连接到 Mac</div>
      </header>

      <section className="upload-hero">
        <p className="eyebrow">华为 P40 Pro · 本地直传</p>
        <h1>把这一刻，<br />送回你的 Mac。</h1>
        <p>可一次选择数百张照片和视频，传输期间请保持本页面打开。</p>
      </section>

      <section className="upload-card">
        <label className="select-button">
          <input
            aria-label="选择照片和视频"
            type="file"
            accept="image/*,video/*"
            multiple
            onChange={(event) => {
              selectFiles(event.target.files);
              event.target.value = "";
            }}
          />
          <span className="plus">＋</span>
          <span><strong>选择照片和视频</strong><small>支持批量选择 · 原画质传输</small></span>
        </label>

        {items.length > 0 && (
          <div className="transfer-panel">
            <div className="transfer-heading">
              <div><strong>{items.length} 个文件</strong><span>{formatBytes(totalBytes)}</span></div>
              <b>{progress}%</b>
            </div>
            <div className="total-progress"><span style={{ width: `${progress}%` }} /></div>
            <div className="transfer-meta">
              <span>{completed} 已完成</span>
              <span>{formatBytes(uploadedBytes)} / {formatBytes(totalBytes)}</span>
            </div>
            <div className="queue-actions">
              {isPaused ? (
                <button type="button" onClick={() => queue.resumeAll()}>继续全部</button>
              ) : (
                <button type="button" onClick={() => void queue.pauseAll()}>暂停全部</button>
              )}
              {failed > 0 && <button type="button" onClick={() => queue.retryFailed()}>重试失败项</button>}
            </div>
            <ul className="file-list">
              {items.slice(0, 100).map((item) => (
                <li key={item.id}>
                  <div className={`file-kind ${item.file.type.startsWith("video") ? "video" : "photo"}`} />
                  <div className="file-copy"><strong>{item.file.name}</strong><span>{formatBytes(item.totalBytes)}</span></div>
                  <span className={`file-state ${item.state}`}>{stateLabels[item.state]}</span>
                </li>
              ))}
            </ul>
            {items.length > 100 && <p className="more-files">另有 {items.length - 100} 个文件正在队列中</p>}
          </div>
        )}
      </section>

      <footer className="mobile-footer">端到端局域网传输 · 文件不会上传到云端</footer>
    </main>
  );
}
