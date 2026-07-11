"""
T4 演示：before/after 技术方案对比
BEFORE = 无 AI，纯关键词匹配条款文本（模拟 Ctrl+F）
AFTER  = LLM + 知识库，结构化预核保分析

虚构案例，零真实隐私，措辞守「参考/预判」
"""
import time
from dotenv import load_dotenv
from src.kb_loader import load_product
from src.naive_search import run_naive_search
from src.underwriting_engine import run_preunderwriting

load_dotenv()

PRODUCT_ID = "darwin12"

CUSTOMER_INFO = (
    "客户基本情况：男，41岁\n"
    "健康情况：\n"
    "- 甲状腺结节3类，半年前体检发现，医生建议随访，未手术未服药\n"
    "- 轻度脂肪肝，无症状，未服药\n"
    "- 血压偏高（135/88），未确诊高血压，未服药\n"
    "- 1年前因急性阑尾炎手术，已痊愈\n"
    "- 无癌症、无糖尿病、无心脏病史"
)


def header(title: str) -> None:
    print()
    print("━" * 64)
    print(f"  {title}")
    print("━" * 64)
    print()


def main() -> None:
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║      健康险预核保：before / after 技术方案对比                  ║")
    print("║      产品：达尔文12号重大疾病保险                               ║")
    print("║      客户：虚构张先生（甲状腺结节 + 脂肪肝 + 阑尾炎术后）         ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print("【客户情况】")
    print(CUSTOMER_INFO)

    product = load_product(PRODUCT_ID)

    # ── BEFORE ──────────────────────────────────────────────────
    header("⏪  BEFORE  —  无 AI，纯关键词匹配（模拟 Ctrl+F 查 PDF）")

    t0 = time.time()
    before_result = run_naive_search(product, CUSTOMER_INFO)
    before_elapsed = time.time() - t0

    print(before_result)
    print(f"\n⏱  耗时：{before_elapsed:.2f} 秒")
    print()
    print("⚠️  上面是原始碎片——代理人需要自己拼凑、判断、打电话问核保，")
    print("    通常 20-45 分钟才能给客户一个大概回答，且没有书面留档。")

    print()
    input("  ── 按 Enter 键查看 AFTER ──")

    # ── AFTER ───────────────────────────────────────────────────
    header("▶▶  AFTER  —  LLM + 知识库，结构化预核保分析")

    print("  正在调用 DeepSeek...", end="", flush=True)
    t0 = time.time()
    after_result = run_preunderwriting(product, CUSTOMER_INFO)
    after_elapsed = time.time() - t0
    print(f" 完成（{after_elapsed:.1f}s）")
    print()
    print(after_result)

    # ── 对比表 ─────────────────────────────────────────────────
    header("📊  对比总结")

    rows = [
        ("维度",          "BEFORE（无 AI）",          "AFTER（LLM + 知识库）"),
        ("响应时间",       "20-45 分钟",               f"实测 {after_elapsed:.0f} 秒"),
        ("查询方式",       "Ctrl+F 关键词碎片",         "语义理解 + 规则推理"),
        ("输出质量",       "原文碎片，需人工研判",        "逐项结论，附原文出处"),
        ("合规留档",       "口头/凭记忆，难溯源",         "结构化文字，可截图存档"),
        ("遗漏风险",       "高（依赖个人经验）",          "低（遍历全部知识库规则）"),
    ]

    col_w = [12, 26, 26]

    def row_line(row: tuple[str, ...]) -> str:
        cells = [str(c).ljust(col_w[i]) for i, c in enumerate(row)]
        return "│" + "│".join(cells) + "│"

    sep = "┼".join("─" * w for w in col_w)
    for i, r in enumerate(rows):
        print(row_line(r))
        if i == 0:
            print("┼" + sep + "┼")

    print()
    print("  ⚠️  所有结果均为预核保参考，最终以保险公司核保决定为准")
    print("  ⚠️  演示案例为虚构，不含任何真实客户隐私数据")
    print()


if __name__ == "__main__":
    main()
