"""只读探测两源；不创建订单，不输出任何凭据或上游错误正文。"""

from datetime import date

import httpx
import typer

from ai_trading.config import Settings
from ai_trading.integrations.china.akshare import AkshareEodProvider
from ai_trading.integrations.china.failover import MarketProvider
from ai_trading.integrations.china.tushare import TushareEodProvider
from ai_trading.integrations.market_data import MarketDataProviderError, MarketDataRequest
from ai_trading.logging_config import configure_logging

app = typer.Typer()


@app.command()
def probe(symbol: str = "600519.SH", trade_date: str = "2026-10-28") -> None:
    settings = Settings()
    configure_logging(settings.project_root / "logs", settings.log_level)
    request = MarketDataRequest(
        symbol=symbol,
        provider_symbol=symbol,
        trade_date=date.fromisoformat(trade_date),
        currency="CNY",
    )
    failures = 0
    with httpx.Client(timeout=20) as client:
        providers: tuple[MarketProvider, ...] = (
            AkshareEodProvider(),
            TushareEodProvider(settings.tushare_token, client),
        )
        for provider in providers:
            name = type(provider).__name__
            try:
                bar = provider.fetch(request)
                typer.echo(f"{name}: 成功 {bar.trade_date} close={bar.close} volume={bar.volume}")
            except MarketDataProviderError as exc:
                failures += 1
                typer.echo(f"{name}: {exc.kind.value} {exc}")
    if failures:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
