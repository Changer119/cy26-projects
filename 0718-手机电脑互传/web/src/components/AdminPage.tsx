import { useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";

import type { AdminConfig } from "../api";

interface AdminPageProps {
  loadConfig: () => Promise<AdminConfig>;
}

export function AdminPage({ loadConfig }: AdminPageProps) {
  const [config, setConfig] = useState<AdminConfig | null>(null);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    loadConfig().then(setConfig).catch((error: Error) => setErrorMessage(error.message));
  }, [loadConfig]);

  return (
    <main className="admin-shell">
      <section className="admin-copy">
        <div className="brand-mark">P2C</div>
        <p className="eyebrow">PHONE2COMPUTER · 本地传输</p>
        <h1>让照片回到<br />你的 Mac。</h1>
        <p className="lead">不经过云端，不使用数据线。手机和电脑只需连接同一个 Wi-Fi。</p>
        <div className="privacy-note"><span />文件只在当前局域网内传输</div>
      </section>

      <section className="pairing-card">
        <p className="step-label">01 / 手机连接</p>
        <h2>用华为手机扫码开始传输</h2>
        {errorMessage && <p className="error-banner">{errorMessage}</p>}
        {!config && !errorMessage && <div className="qr-placeholder">正在生成安全二维码…</div>}
        {config && (
          <>
            <div className="qr-frame">
              <QRCodeSVG value={config.upload_url} size={228} level="M" />
            </div>
            <p className="pairing-url">{config.upload_url}</p>
            <div className="destination">
              <span>接收目录</span>
              <strong>{config.output_directory}</strong>
            </div>
          </>
        )}
      </section>
    </main>
  );
}
