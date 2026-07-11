"""强类型数据模型：台风路径点、预报路径、大屏数据包。"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


def _to_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value))
    except ValueError:
        return None


class WindRadius(BaseModel):
    """风圈四象限半径（公里），顺序：东北、东南、西南、西北。"""

    ne: float | None = None
    se: float | None = None
    sw: float | None = None
    nw: float | None = None

    @classmethod
    def parse(cls, raw: str | None) -> "WindRadius | None":
        if not raw:
            return None
        parts = [_to_float(p) for p in str(raw).split("|")]
        if len(parts) != 4 or all(p is None for p in parts):
            return None
        return cls(ne=parts[0], se=parts[1], sw=parts[2], nw=parts[3])


class ForecastPoint(BaseModel):
    """单个预报点。"""

    time: str
    lng: float
    lat: float
    strong: str = ""
    power: float | None = None
    speed: float | None = None
    pressure: float | None = None

    @field_validator("power", "speed", "pressure", mode="before")
    @classmethod
    def _num(cls, v: object) -> float | None:
        return _to_float(v)


class ForecastTrack(BaseModel):
    """某一预报机构给出的预报路径。"""

    agency: str = Field(description="预报机构，如 中国/日本/美国")
    points: list[ForecastPoint] = []


class TrackPoint(BaseModel):
    """历史（实况）路径点。"""

    time: str
    lng: float
    lat: float
    strong: str = ""
    power: float | None = None
    speed: float | None = None
    pressure: float | None = None
    move_speed: float | None = None
    move_direction: str = ""
    radius7: WindRadius | None = None
    radius10: WindRadius | None = None
    radius12: WindRadius | None = None
    ck_position: str = Field(default="", description="相对位置描述，如：距离温岭市东南约120公里")
    summary: str = Field(default="", description="趋势简述")

    @field_validator("power", "speed", "pressure", "move_speed", mode="before")
    @classmethod
    def _num(cls, v: object) -> float | None:
        return _to_float(v)


class Landfall(BaseModel):
    """登陆信息（字段以数据源为准，允许扩展）。"""

    model_config = {"extra": "allow"}

    landtime: str = ""
    landaddress: str = ""
    landstrong: str = ""


class TyphoonDetail(BaseModel):
    """台风完整信息。"""

    tfid: str
    name: str
    enname: str
    is_active: bool
    start_time: str = ""
    end_time: str = ""
    land: list[Landfall] = []
    points: list[TrackPoint] = []
    forecasts: list[ForecastTrack] = Field(default=[], description="最新一个实况点携带的各机构预报路径")


class DashboardData(BaseModel):
    """提供给大屏前端的数据包。"""

    typhoon: TyphoonDetail
    fetched_at: str = Field(description="后端抓取数据的时间")
    source: str = "浙江省水利厅 · 台风路径实时发布系统"
    refresh_interval: int = Field(description="前端刷新周期（秒）")
