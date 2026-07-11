"""台风数据抓取与缓存：每 60 秒从数据源拉取一次最新数据。"""

from __future__ import annotations

import asyncio
from datetime import datetime

import httpx

from app.config import API_BASE, HTTP_TIMEOUT_SECONDS, REFRESH_INTERVAL_SECONDS, TARGET_ENNAME, TARGET_TFID
from app.logger import get_logger
from app.models import (
    DashboardData,
    ForecastPoint,
    ForecastTrack,
    Landfall,
    TrackPoint,
    TyphoonDetail,
    WindRadius,
)

logger = get_logger("fetcher")


def _parse_track_point(raw: dict) -> TrackPoint:
    return TrackPoint(
        time=raw.get("time", ""),
        lng=float(raw["lng"]),
        lat=float(raw["lat"]),
        strong=raw.get("strong") or "",
        power=raw.get("power"),
        speed=raw.get("speed"),
        pressure=raw.get("pressure"),
        move_speed=raw.get("movespeed"),
        move_direction=raw.get("movedirection") or "",
        radius7=WindRadius.parse(raw.get("radius7")),
        radius10=WindRadius.parse(raw.get("radius10")),
        radius12=WindRadius.parse(raw.get("radius12")),
        ck_position=(raw.get("ckposition") or "").strip(),
        summary=(raw.get("jl") or "").strip(),
    )


def _parse_forecasts(raw_point: dict) -> list[ForecastTrack]:
    tracks: list[ForecastTrack] = []
    for item in raw_point.get("forecast") or []:
        points = [
            ForecastPoint(
                time=p.get("time", ""),
                lng=float(p["lng"]),
                lat=float(p["lat"]),
                strong=p.get("strong") or "",
                power=p.get("power"),
                speed=p.get("speed"),
                pressure=p.get("pressure"),
            )
            for p in item.get("forecastpoints") or []
        ]
        if points:
            tracks.append(ForecastTrack(agency=item.get("tm", "未知"), points=points))
    return tracks


def parse_detail(raw: dict) -> TyphoonDetail:
    points = [_parse_track_point(p) for p in raw.get("points") or []]
    forecasts = _parse_forecasts(raw["points"][-1]) if raw.get("points") else []
    return TyphoonDetail(
        tfid=str(raw.get("tfid", "")),
        name=raw.get("name", ""),
        enname=raw.get("enname", ""),
        is_active=str(raw.get("isactive", "0")) == "1",
        start_time=raw.get("starttime") or "",
        end_time=raw.get("endtime") or "",
        land=[Landfall.model_validate(x) for x in raw.get("land") or []],
        points=points,
        forecasts=forecasts,
    )


async def _resolve_tfid(client: httpx.AsyncClient) -> str:
    """优先使用配置的台风编号；失败时按英文名在年度列表中查找。"""
    try:
        year = datetime.now().year
        resp = await client.get(f"{API_BASE}/TyphoonList/{year}")
        resp.raise_for_status()
        for item in resp.json():
            if item.get("enname") == TARGET_ENNAME or item.get("tfid") == TARGET_TFID:
                return str(item["tfid"])
    except Exception as exc:  # noqa: BLE001 - 列表查询失败不致命
        logger.warning("台风列表查询失败，回退到配置编号 %s：%s", TARGET_TFID, exc)
    return TARGET_TFID


async def fetch_dashboard_data() -> DashboardData:
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS, verify=False) as client:
        tfid = await _resolve_tfid(client)
        resp = await client.get(f"{API_BASE}/TyphoonInfo/{tfid}")
        resp.raise_for_status()
        detail = parse_detail(resp.json())
    return DashboardData(
        typhoon=detail,
        fetched_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        refresh_interval=REFRESH_INTERVAL_SECONDS,
    )


class TyphoonCache:
    """内存缓存 + 后台定时刷新。"""

    def __init__(self) -> None:
        self._data: DashboardData | None = None
        self._lock = asyncio.Lock()

    @property
    def data(self) -> DashboardData | None:
        return self._data

    async def refresh(self) -> bool:
        async with self._lock:
            try:
                self._data = await fetch_dashboard_data()
                latest = self._data.typhoon.points[-1] if self._data.typhoon.points else None
                logger.info(
                    "数据刷新成功：%s(%s) 实况点 %d 个，最新 %s",
                    self._data.typhoon.name,
                    self._data.typhoon.tfid,
                    len(self._data.typhoon.points),
                    latest.time if latest else "无",
                )
                return True
            except Exception as exc:  # noqa: BLE001 - 刷新失败保留旧数据
                logger.error("数据刷新失败（保留上次数据）：%s", exc)
                return False

    async def run_forever(self) -> None:
        while True:
            await self.refresh()
            await asyncio.sleep(REFRESH_INTERVAL_SECONDS)


cache = TyphoonCache()
