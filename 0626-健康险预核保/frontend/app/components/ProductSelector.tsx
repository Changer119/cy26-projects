"use client";

import { ProductInfo } from "@/lib/api";

interface Props {
  products: ProductInfo[];
  selected: string;
  onChange: (id: string) => void;
}

export default function ProductSelector({ products, selected, onChange }: Props) {
  return (
    <div className="flex gap-3 flex-wrap">
      {products.map((p) => (
        <button
          key={p.id}
          onClick={() => onChange(p.id)}
          className={`
            px-4 py-3 rounded-xl border-2 text-left transition-all
            ${selected === p.id
              ? "border-blue-600 bg-blue-50 text-blue-800"
              : "border-gray-200 bg-white text-gray-700 hover:border-blue-300"
            }
          `}
        >
          <div className="font-semibold text-sm">{p.name}</div>
          <div className="text-xs text-gray-500 mt-0.5">{p.insurer}</div>
          <span className="inline-block mt-1 text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">
            {p.product_type}
          </span>
        </button>
      ))}
    </div>
  );
}
