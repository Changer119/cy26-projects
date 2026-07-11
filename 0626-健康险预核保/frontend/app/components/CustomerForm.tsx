"use client";

import { DemoCase } from "@/lib/api";

interface Props {
  value: string;
  onChange: (v: string) => void;
  demoCases: DemoCase[];
  onSubmit: () => void;
  loading: boolean;
}

export default function CustomerForm({ value, onChange, demoCases, onSubmit, loading }: Props) {
  return (
    <div className="space-y-3">
      <div className="flex gap-2 flex-wrap items-center">
        <span className="text-sm text-gray-500">快速填入案例：</span>
        {demoCases.map((c) => (
          <button
            key={c.label}
            onClick={() => onChange(c.customer_info)}
            className="text-xs px-3 py-1 rounded-full border border-blue-200 text-blue-600 hover:bg-blue-50 transition"
          >
            {c.label}
          </button>
        ))}
      </div>

      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={
          "请输入客户健康情况，例如：\n" +
          "男，45岁\n" +
          "甲状腺结节3类，未手术\n" +
          "轻度脂肪肝，无症状\n" +
          "无重大疾病史"
        }
        rows={7}
        className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-400 font-mono leading-relaxed"
      />

      <button
        onClick={onSubmit}
        disabled={!value.trim() || loading}
        className="w-full py-3 rounded-xl bg-blue-600 text-white font-semibold text-sm hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition"
      >
        {loading ? "AI 分析中..." : "开始预核保"}
      </button>
    </div>
  );
}
