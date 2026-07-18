import { useEffect, useState } from "react";

import { loadDashboardData } from "./api";
import { DashboardShell, type ViewId } from "./components/Shell";
import { DataHealthPage } from "./pages/DataHealthPage";
import { OrdersPage } from "./pages/OrdersPage";
import { PerformancePage } from "./pages/PerformancePage";
import { PortfolioPage } from "./pages/PortfolioPage";
import { TodayPage } from "./pages/TodayPage";
import { WatchlistPage } from "./pages/WatchlistPage";
import type { DashboardData } from "./types";

export type DashboardLoader = () => Promise<DashboardData>;

interface AppProps {
  readonly loader?: DashboardLoader;
}

export default function App({ loader = loadDashboardData }: AppProps) {
  const [view, setView] = useState<ViewId>("today");
  const [data, setData] = useState<DashboardData | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    void loader()
      .then((result) => {
        if (active) setData(result);
      })
      .catch(() => {
        if (active) setFailed(true);
      });
    return () => {
      active = false;
    };
  }, [loader]);

  if (data === null) {
    return (
      <div className="grid min-h-screen place-items-center bg-[#07101b] text-slate-200">
        <div className="text-center">
          <p className="font-mono text-xs tracking-[0.24em] text-cyan-400">AI PAPER TRADING</p>
          <p className="mt-4 text-sm text-slate-500">{failed ? "本地 API 连接失败" : "正在读取本地账本…"}</p>
        </div>
      </div>
    );
  }

  return (
    <DashboardShell
      account={data.account}
      onViewChange={setView}
      unavailableCount={data.unavailableSections.length}
      view={view}
    >
      {view === "today" && <TodayPage account={data.account} plans={data.plans} />}
      {view === "portfolio" && <PortfolioPage account={data.account} />}
      {view === "watchlist" && <WatchlistPage items={data.watchlist} />}
      {view === "orders" && <OrdersPage orders={data.orders} />}
      {view === "performance" && <PerformancePage account={data.account} points={data.performance} />}
      {view === "health" && <DataHealthPage items={data.dataHealth} />}
    </DashboardShell>
  );
}
