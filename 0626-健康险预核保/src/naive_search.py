"""
BEFORE 方案：纯关键词匹配，无 AI
模拟代理人手动在条款中 Ctrl+F 的效果
"""
import re
from typing import Any


def _extract_keywords(customer_info: str) -> list[str]:
    """从客户描述中提取关键词（简单分词）"""
    stopwords = {
        "是否", "客户", "基本情况", "健康情况", "男", "女", "岁",
        "发现", "已", "未", "无", "有", "和", "或", "及", "的",
        "因", "于", "在", "了", "并", "被", "曾", "需", "可",
    }
    tokens = re.split(r"[，。、\n\s\-（）()：:？?！!]", customer_info)
    keywords = []
    for t in tokens:
        t = t.strip()
        if len(t) >= 2 and t not in stopwords:
            keywords.append(t)
    return list(dict.fromkeys(keywords))  # 去重保序


def _search_in_text(text: str, keywords: list[str]) -> list[str]:
    hits = []
    for kw in keywords:
        if kw in text:
            start = max(0, text.index(kw) - 30)
            end = min(len(text), text.index(kw) + len(kw) + 60)
            snippet = "..." + text[start:end].replace("\n", " ") + "..."
            hits.append(f"[匹配词: {kw}]  {snippet}")
    return hits


def run_naive_search(product: dict[str, Any], customer_info: str) -> str:
    """
    无 AI 的暴力文本搜索：
    把知识库里所有 source_text 拼在一起，对客户信息关键词做 Ctrl+F
    """
    keywords = _extract_keywords(customer_info)

    # 把所有条款原文拼成一段大文本（模拟打开 PDF 全文搜索）
    corpus_lines: list[str] = []
    for q in product.get("health_disclosure_questions", []):
        corpus_lines.append(q.get("source_text", ""))
    for r in product.get("underwriting_rules", []):
        corpus_lines.append(r.get("source_text", ""))
    corpus = "\n".join(corpus_lines)

    results: list[str] = []
    matched_kws: list[str] = []

    for kw in keywords:
        if kw in corpus:
            matched_kws.append(kw)
            hits = _search_in_text(corpus, [kw])
            results.extend(hits)

    unmatched = [k for k in keywords if k not in matched_kws]

    lines = [
        f"产品：{product.get('product_name', '')}",
        f"关键词提取（共 {len(keywords)} 个）：{', '.join(keywords)}",
        "",
        f"命中关键词（{len(matched_kws)} 个）：{', '.join(matched_kws) or '无'}",
        "─" * 56,
    ]

    if results:
        for r in results:
            lines.append(r)
    else:
        lines.append("未找到匹配条款。")

    if unmatched:
        lines.append("")
        lines.append(f"未命中关键词（{len(unmatched)} 个，条款中找不到）：{', '.join(unmatched)}")

    lines.append("─" * 56)
    lines.append("（以上为原始条款碎片，无结构化结论，需人工研判）")

    return "\n".join(lines)
