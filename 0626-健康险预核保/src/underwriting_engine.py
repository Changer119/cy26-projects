import logging
import os
from openai import OpenAI
from .kb_loader import format_kb_for_prompt

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是专业的健康险预核保助手。你的任务是根据提供的产品核保规则知识库，对客户的健康情况给出预核保建议。

## 严格规则
1. 只能基于知识库中明确列出的规则给出结论，禁止凭空编造核保判断
2. 每条结论必须引用知识库中的原文（用「」标注）
3. 结论类型只能是：标准体承保 / 需人工核保 / 除外承保 / 延期 / 拒保
4. 如知识库中无明确规定，必须注明"知识库暂无相关规则，建议人工核保"
5. 措辞必须使用"参考/预判"，禁止说"保证能过"或"一定不赔"

## 输出格式
请按以下结构输出：

**综合预核保结论**：[标准体承保 / 需人工核保 / 除外承保 / 延期 / 拒保]

**逐项分析**：
| 客户情况 | 对应条款 | 核保结论 | 原文依据 |
|---------|---------|---------|---------|
| ... | ... | ... | 「...」|

**重要提示**：
- 本结果为预核保参考，最终以保险公司核保决定为准
- [其他需要特别说明的事项]"""


def build_user_message(kb_text: str, customer_info: str) -> str:
    return f"""请根据以下知识库，对客户健康情况进行预核保评估。

=== 产品知识库 ===
{kb_text}

=== 客户健康情况 ===
{customer_info}

请给出预核保建议。"""


def run_preunderwriting(
    product: dict,
    customer_info: str,
) -> str:
    client = OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url=os.environ["DEEPSEEK_BASE_URL"],
    )
    model = os.environ["DEEPSEEK_MODEL"]

    kb_text = format_kb_for_prompt(product)
    user_msg = build_user_message(kb_text, customer_info)

    logger.info("调用 LLM 进行预核保评估，产品：%s", product["product_name"])

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.1,
    )

    result = response.choices[0].message.content
    logger.info("预核保评估完成")
    return result
