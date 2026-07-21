import { useMemo } from "react";

import { consumePairingToken, loadAdminConfig } from "./api";
import { AdminPage } from "./components/AdminPage";
import { UploadPage } from "./components/UploadPage";
import { createTusRunner } from "./upload";

export function App() {
  const isAdmin = window.location.pathname === "/admin";
  const token = useMemo(() => {
    if (isAdmin) return null;
    return consumePairingToken(
      new URL(window.location.href),
      window.sessionStorage,
      (data, unused, url) => window.history.replaceState(data, unused, url),
    );
  }, [isAdmin]);
  const runner = useMemo(() => (token ? createTusRunner(token) : null), [token]);

  if (isAdmin) {
    return <AdminPage loadConfig={loadAdminConfig} />;
  }
  if (!runner) {
    return (
      <main className="disconnected-shell">
        <div className="brand-mark">P2C</div>
        <p className="eyebrow">PHONE2COMPUTER</p>
        <h1>连接已经失效</h1>
        <p>请回到 Mac 管理页面，重新扫描二维码。</p>
      </main>
    );
  }
  return <UploadPage runner={runner} />;
}
