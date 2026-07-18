const cnyFormatter = new Intl.NumberFormat("zh-CN", {
  style: "currency",
  currency: "CNY",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatMicros(value: number): string {
  return cnyFormatter.format(value / 1_000_000);
}

export function formatBps(value: number): string {
  const percentage = value / 100;
  const sign = percentage > 0 ? "+" : "";
  return `${sign}${percentage.toFixed(2)}%`;
}
