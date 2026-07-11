from pydantic import BaseModel


class ProductInfo(BaseModel):
    id: str
    name: str
    insurer: str
    product_type: str


class UnderwriteRequest(BaseModel):
    product_id: str
    customer_info: str


class UnderwriteResponse(BaseModel):
    product_name: str
    result: str
    elapsed_seconds: float


class DemoCase(BaseModel):
    label: str
    customer_info: str
