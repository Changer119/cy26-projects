"use client";

import { useEffect, useState } from "react";
import {
  fetchProducts,
  fetchDemoCases,
  runUnderwrite,
  ProductInfo,
  DemoCase,
  UnderwriteResult,
} from "@/lib/api";
import ProductSelector from "@/app/components/ProductSelector";
import CustomerForm from "@/app/components/CustomerForm";
import ResultPanel from "@/app/components/ResultPanel";

export default function Home() {
  const [products, setProducts] = useState<ProductInfo[]>([]);
  const [demoCases, setDemoCases] = useState<DemoCase[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<string>("");
  const [customerInfo, setCustomerInfo] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<UnderwriteResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchProducts().then((ps) => {
      setProducts(ps);
      if (ps.length > 0) setSelectedProduct(ps[0].id);
    });
    fetchDemoCases().then(setDemoCases);
  }, []);

  async function handleSubmit() {
    if (!selectedProduct || !customerInfo.trim()) return;
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const r = await runUnderwrite(selectedProduct, customerInfo);
      setResult(r);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "未知错误");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-gray-900">健康险智能预核保</h1>
            <p className="text-xs text-gray-500 mt-0.5">仅供代理人参考，结果为预判而非承保承诺</p>
          </div>
          <span className="text-xs px-2 py-1 rounded bg-blue-100 text-blue-700">Demo</span>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8 space-y-8">
        <section className="bg-white rounded-2xl border border-gray-200 p-6 space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">第一步：选择险种</h2>
          <ProductSelector
            products={products}
            selected={selectedProduct}
            onChange={setSelectedProduct}
          />
        </section>

        <section className="bg-white rounded-2xl border border-gray-200 p-6 space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">第二步：录入客户健康情况</h2>
          <CustomerForm
            value={customerInfo}
            onChange={setCustomerInfo}
            demoCases={demoCases}
            onSubmit={handleSubmit}
            loading={loading}
          />
        </section>

        {loading && (
          <div className="flex items-center gap-3 text-blue-600 text-sm py-4">
            <span className="animate-spin inline-block text-xl">⟳</span>
            <span>AI 正在逐条核对条款规则，请稍候...</span>
          </div>
        )}

        {error && (
          <div className="rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            ❌ {error}
          </div>
        )}

        {result && (
          <section className="bg-white rounded-2xl border border-gray-200 p-6 space-y-3">
            <h2 className="text-sm font-semibold text-gray-700">预核保结果</h2>
            <ResultPanel result={result} />
          </section>
        )}
      </main>
    </div>
  );
}
