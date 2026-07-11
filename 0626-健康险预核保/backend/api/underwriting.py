import time
from fastapi import APIRouter, HTTPException
from backend.models.schemas import (
    ProductInfo,
    UnderwriteRequest,
    UnderwriteResponse,
    DemoCase,
)
from src.kb_loader import load_product, list_products
from src.underwriting_engine import run_preunderwriting

router = APIRouter(prefix="/api")

DEMO_CASES: list[DemoCase] = [
    DemoCase(
        label="高血压（控制良好）",
        customer_info=(
            "男，52岁\n"
            "确诊高血压3年，目前服用氨氯地平，血压控制在130/80左右\n"
            "无其他疾病，无手术史"
        ),
    ),
    DemoCase(
        label="甲状腺结节 + 脂肪肝（虚构）",
        customer_info=(
            "男，41岁\n"
            "甲状腺结节3类，半年前体检发现，医生建议随访，未手术未服药\n"
            "轻度脂肪肝，无症状，未服药\n"
            "血压偏高（135/88），未确诊高血压，未服药\n"
            "1年前因急性阑尾炎手术，已痊愈\n"
            "无癌症、无糖尿病、无心脏病史"
        ),
    ),
    DemoCase(
        label="糖尿病 + 高血压 + 心绞痛（虚构）",
        customer_info=(
            "男，58岁\n"
            "2型糖尿病10年，口服二甲双胍，空腹血糖7.2\n"
            "高血压8年，服用降压药，血压控制稳定\n"
            "3年前确诊不稳定型心绞痛，曾住院治疗，现服用阿司匹林和他汀类药物\n"
            "无脑卒中、无肾病、无手术史"
        ),
    ),
]


@router.get("/products", response_model=list[ProductInfo])
def get_products() -> list[ProductInfo]:
    products = list_products()
    return [
        ProductInfo(
            id=p["product_id"],
            name=p["product_name"],
            insurer=p["insurer"],
            product_type=p["product_type"],
        )
        for p in products
    ]


@router.get("/demo-cases", response_model=list[DemoCase])
def get_demo_cases() -> list[DemoCase]:
    return DEMO_CASES


@router.post("/underwrite", response_model=UnderwriteResponse)
def underwrite(req: UnderwriteRequest) -> UnderwriteResponse:
    try:
        product = load_product(req.product_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"产品 {req.product_id} 不存在")

    t0 = time.time()
    result = run_preunderwriting(product, req.customer_info)
    elapsed = time.time() - t0

    return UnderwriteResponse(
        product_name=product["product_name"],
        result=result,
        elapsed_seconds=round(elapsed, 1),
    )
