import logging
import sys
from dotenv import load_dotenv
from src.kb_loader import load_product, PRODUCT_FILES
from src.underwriting_engine import run_preunderwriting

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

PRODUCT_MENU = {
    "1": ("darwin12", "达尔文12号重大疾病保险"),
    "2": ("xinyi_medical", "心医保（长生版）长期医疗险"),
}

DEMO_CASES = [
    {
        "label": "案例一：高血压客户（控制良好）",
        "customer_info": (
            "客户基本情况：男，38岁\n"
            "健康情况：\n"
            "- 高血压2年，目前服用一种降压药，血压控制在130/85，无并发症\n"
            "- 无糖尿病、无心脏病史\n"
            "- 2年内无住院手术史\n"
            "- 非吸烟者"
        ),
    },
    {
        "label": "案例二：甲状腺结节客户",
        "customer_info": (
            "客户基本情况：女，32岁\n"
            "健康情况：\n"
            "- 3个月前体检发现甲状腺结节，TI-RADS 3类，医生建议定期复查\n"
            "- 未手术，未服药\n"
            "- 无其他既往病史\n"
            "- 无近期住院手术史"
        ),
    },
    {
        "label": "案例三：糖尿病+高血压",
        "customer_info": (
            "客户基本情况：男，52岁\n"
            "健康情况：\n"
            "- 2型糖尿病5年，服用二甲双胍，血糖控制一般（HbA1c 7.5%）\n"
            "- 高血压3年，服药控制\n"
            "- 1年前因心绞痛住院，未做支架手术\n"
            "- 无癌症史"
        ),
    },
]


def print_separator(char: str = "=", width: int = 60) -> None:
    print(char * width)


def select_product() -> dict:
    print_separator()
    print("请选择产品：")
    for key, (_, name) in PRODUCT_MENU.items():
        print(f"  {key}. {name}")
    print("  0. 退出")
    print_separator("-")

    while True:
        choice = input("输入序号：").strip()
        if choice == "0":
            sys.exit(0)
        if choice in PRODUCT_MENU:
            product_id, product_name = PRODUCT_MENU[choice]
            print(f"\n已选择：{product_name}")
            return load_product(product_id)
        print("无效输入，请重新选择")


def get_customer_info() -> str:
    print_separator()
    print("输入客户健康情况（输入完毕后按两次回车）：")
    print("  或输入 demo 使用示例案例")
    print_separator("-")

    first_line = input().strip()
    if first_line.lower() == "demo":
        return select_demo_case()

    lines = [first_line]
    while True:
        line = input()
        if line == "" and lines and lines[-1] == "":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def select_demo_case() -> str:
    print_separator()
    print("选择演示案例：")
    for i, case in enumerate(DEMO_CASES, 1):
        print(f"  {i}. {case['label']}")
    print_separator("-")

    while True:
        choice = input("输入序号：").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(DEMO_CASES):
                case = DEMO_CASES[idx]
                print(f"\n【{case['label']}】")
                print(case["customer_info"])
                return case["customer_info"]
        except ValueError:
            pass
        print("无效输入，请重新选择")


def main() -> None:
    print_separator()
    print("  健康险预核保助手  v0.1")
    print("  ⚠️  本工具仅供参考，最终以保险公司核保决定为准")
    print_separator()

    product = select_product()
    customer_info = get_customer_info()

    print_separator()
    print("正在评估，请稍候...")
    print_separator("-")

    result = run_preunderwriting(product, customer_info)

    print_separator()
    print(f"【{product['product_name']}】预核保结果")
    print_separator("-")
    print(result)
    print_separator()


if __name__ == "__main__":
    main()
