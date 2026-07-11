import json
from pathlib import Path
from typing import Any

KB_DIR = Path(__file__).parent.parent / "knowledge_base"

PRODUCT_FILES = {
    "darwin12": "darwin12.json",
    "xinyi_medical": "xinyi_medical.json",
}


def load_product(product_id: str) -> dict[str, Any]:
    if product_id not in PRODUCT_FILES:
        raise FileNotFoundError(f"未知产品 ID: {product_id}")
    filepath = KB_DIR / PRODUCT_FILES[product_id]
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def list_products() -> list[dict[str, Any]]:
    """返回所有产品的摘要信息（不含完整规则）"""
    result = []
    for pid in PRODUCT_FILES:
        p = load_product(pid)
        result.append({
            "product_id": p["product_id"],
            "product_name": p["product_name"],
            "insurer": p["insurer"],
            "product_type": p["product_type"],
        })
    return result


def load_all_products() -> dict[str, dict[str, Any]]:
    return {pid: load_product(pid) for pid in PRODUCT_FILES}


def format_kb_for_prompt(product: dict[str, Any]) -> str:
    """将产品知识库格式化为 LLM prompt 可用的文本"""
    lines = [
        f"【产品】{product['product_name']}",
        f"【承保公司】{product['insurer']}",
        f"【条款文件号】{product['policy_doc_number']}",
        f"【产品类型】{product['product_type']}",
        "",
        "=== 基本信息 ===",
        f"等待期：{product['basic_info']['waiting_period_days']}天",
        f"等待期说明：{product['basic_info']['waiting_period_note']}",
        "",
        "=== 健康告知问题及核保规则 ===",
    ]

    for q in product["health_disclosure_questions"]:
        lines.append(f"\n[{q['id']}] 问题：{q['question']}")
        lines.append(f"  → 回答「是」：{q['answer_yes_action']}")
        lines.append(f"  → 回答「否」：{q['answer_no_action']}")
        lines.append(f"  条款依据：{q['source_clause']}")
        lines.append(f"  原文：「{q['source_text']}」")

    lines.append("\n=== 核保规则明细 ===")
    for rule in product["underwriting_rules"]:
        lines.append(f"\n【情形】{rule['condition']}")
        lines.append(f"  核保结论：{rule['action']}")
        if rule.get("exception"):
            lines.append(f"  例外：{rule['exception']}")
        lines.append(f"  条款：{rule['source_clause']}")
        lines.append(f"  原文：「{rule['source_text']}」")

    lines.append("\n=== 重要说明 ===")
    for note in product.get("important_notes", []):
        lines.append(f"• {note}")

    return "\n".join(lines)
