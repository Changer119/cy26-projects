import type { PerformancePoint } from "../types";

function chartPath(points: readonly PerformancePoint[]): string {
  if (points.length === 0) return "";
  const values = points.map((point) => point.navMicros);
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const spread = Math.max(maximum - minimum, 1);
  return points
    .map((point, index) => {
      const x = points.length === 1 ? 50 : (index / (points.length - 1)) * 100;
      const y = 82 - ((point.navMicros - minimum) / spread) * 64;
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}

export function PerformanceChart({ points }: { readonly points: readonly PerformancePoint[] }) {
  return (
    <div className="relative h-64 overflow-hidden rounded-lg border border-white/8 bg-[#091521] p-4">
      <div className="absolute inset-x-4 top-1/4 border-t border-dashed border-white/5" />
      <div className="absolute inset-x-4 top-1/2 border-t border-dashed border-white/5" />
      <div className="absolute inset-x-4 top-3/4 border-t border-dashed border-white/5" />
      {points.length === 0 ? (
        <div className="grid h-full place-items-center text-sm text-slate-500">等待首个净值快照</div>
      ) : (
        <svg aria-label="组合净值曲线" className="relative h-full w-full" preserveAspectRatio="none" viewBox="0 0 100 100">
          <path d={`${chartPath(points)} L 100 100 L 0 100 Z`} fill="rgba(34,211,238,0.08)" />
          <path d={chartPath(points)} fill="none" stroke="#22d3ee" strokeWidth="1.2" vectorEffect="non-scaling-stroke" />
        </svg>
      )}
    </div>
  );
}
