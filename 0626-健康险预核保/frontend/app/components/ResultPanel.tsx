"use client";

import { UnderwriteResult } from "@/lib/api";

interface Props {
  result: UnderwriteResult;
}

function parseMarkdownTable(text: string): { rows: string[][] } | null {
  const lines = text.split("\n").filter((l) => l.trim().startsWith("|"));
  if (lines.length < 2) return null;
  const rows = lines
    .filter((l) => !/^\|[-| ]+\|$/.test(l.trim()))
    .map((l) =>
      l
        .split("|")
        .slice(1, -1)
        .map((c) => c.trim())
    );
  return { rows };
}

function renderResult(text: string) {
  const blocks = text.split("\n\n");
  return blocks.map((block, i) => {
    const tableData = parseMarkdownTable(block);
    if (tableData && tableData.rows.length >= 2) {
      const [header, ...body] = tableData.rows;
      return (
        <div key={i} className="overflow-x-auto rounded-xl border border-gray-200 mt-4">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50">
                {header.map((h, j) => (
                  <th key={j} className="px-4 py-2 text-left font-medium text-gray-600 border-b border-gray-200">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {body.map((row, j) => (
                <tr key={j} className="border-b border-gray-100 hover:bg-gray-50">
                  {row.map((cell, k) => (
                    <td key={k} className="px-4 py-3 text-gray-700 align-top leading-relaxed">
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }

    // Bold lines (** ... **)
    const formatted = block
      .split("\n")
      .map((line, j) => {
        const bold = line.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
        const bullet = line.trim().startsWith("-") || line.trim().startsWith("•");
        if (bullet) {
          return (
            <li
              key={j}
              className="ml-4 text-gray-700 text-sm"
              dangerouslySetInnerHTML={{ __html: bold.replace(/^[-•]\s*/, "") }}
            />
          );
        }
        return (
          <p
            key={j}
            className="text-sm text-gray-800 leading-relaxed"
            dangerouslySetInnerHTML={{ __html: bold }}
          />
        );
      });

    return <div key={i} className="mt-2 space-y-1">{formatted}</div>;
  });
}

function conclusionBadge(text: string) {
  if (text.includes("标准体") && text.includes("可承保")) {
    return { label: "标准体可承保", color: "bg-green-100 text-green-800 border-green-200" };
  }
  if (text.includes("拒保")) {
    return { label: "建议拒保", color: "bg-red-100 text-red-800 border-red-200" };
  }
  return { label: "需人工核保", color: "bg-yellow-100 text-yellow-800 border-yellow-200" };
}

export default function ResultPanel({ result }: Props) {
  const badge = conclusionBadge(result.result);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <span className="text-xs text-gray-500">产品：</span>
          <span className="text-sm font-medium text-gray-800">{result.product_name}</span>
        </div>
        <div className="flex items-center gap-3">
          <span className={`px-3 py-1 rounded-full border text-sm font-semibold ${badge.color}`}>
            {badge.label}
          </span>
          <span className="text-xs text-gray-400">耗时 {result.elapsed_seconds}s</span>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5">
        {renderResult(result.result)}
      </div>

      <div className="rounded-xl bg-amber-50 border border-amber-200 px-4 py-3 text-xs text-amber-700 space-y-1">
        <p>⚠️ 以上结果为预核保参考，最终以保险公司核保决定为准，不构成承保承诺。</p>
        <p>⚠️ 请确保客户如实告知健康情况，否则保险公司有权依法解除合同。</p>
      </div>
    </div>
  );
}
