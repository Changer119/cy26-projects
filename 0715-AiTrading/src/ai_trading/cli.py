from datetime import date, datetime
from pathlib import Path
from typing import Annotated
from zoneinfo import ZoneInfo

import typer
from pydantic import BaseModel, SecretStr

from ai_trading.application import TradingApplication, build_application
from ai_trading.application.runtime import load_market_data, load_strategy_data
from ai_trading.config import Settings
from ai_trading.logging_config import configure_logging
from ai_trading.secrets import LocalSecrets, write_local_secrets

app = typer.Typer(
    name="ai-trading",
    help="A 股与港股模拟交易系统；永久禁用券商连接。",
    no_args_is_help=True,
)


def _application() -> TradingApplication:
    return build_application(Settings())


def _emit(model: BaseModel) -> None:
    typer.echo(model.model_dump_json())


def _parse_date(value: str | None, *, default_today: bool) -> date:
    if value is None:
        if default_today:
            return datetime.now(ZoneInfo("Asia/Shanghai")).date()
        raise typer.BadParameter("必须提供日期")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter("日期必须使用 YYYY-MM-DD") from exc


@app.command("init")
def init_command() -> None:
    """创建 SQLite schema、10 万元模拟账户和默认自选股。"""

    _emit(_application().initialize())


@app.command("status")
def status_command() -> None:
    """输出可机器校验的本地运行状态。"""

    _emit(_application().status())


@app.command("data-smoke")
def data_smoke_command(
    trade_date: Annotated[str | None, typer.Option("--date")] = None,
) -> None:
    """只读验证双源行情，不调用模型或创建模拟订单。"""

    selected = _parse_date(trade_date, default_today=False)
    settings = Settings()
    configure_logging(settings.project_root / "logs", settings.log_level)
    _emit(load_market_data(settings, selected))


@app.command("strategy-smoke")
def strategy_smoke_command(
    trade_date: Annotated[str | None, typer.Option("--date")] = None,
) -> None:
    """只读验证 V2 连续历史与特征，不调用模型或创建模拟订单。"""

    selected = _parse_date(trade_date, default_today=False)
    settings = Settings()
    configure_logging(settings.project_root / "logs", settings.log_level)
    _emit(load_strategy_data(settings, selected))


@app.command("configure-from-env")
def configure_from_env_command(
    destination: Annotated[Path, typer.Option("--destination")] = Path(".env"),
) -> None:
    """把当前进程中的密钥安全落盘，不在终端回显密钥。"""

    settings = Settings()
    if settings.deepseek_api_key is None:
        raise typer.BadParameter("缺少 DEEPSEEK_API_KEY")
    if settings.feishu_target_id is None:
        raise typer.BadParameter("缺少 FEISHU_TARGET_ID")
    write_local_secrets(
        destination,
        LocalSecrets(
            deepseek_api_key=settings.deepseek_api_key,
            tiingo_api_key=settings.tiingo_api_key or SecretStr(""),
            feishu_target_type=settings.feishu_target_type,
            feishu_target_id=settings.feishu_target_id,
        ),
    )
    typer.echo(f"本机配置已安全写入：{destination}")


@app.command("premarket")
def premarket_command(
    trade_date: Annotated[str | None, typer.Option("--date")] = None,
) -> None:
    """生成提案并在本地数据门与风控通过后冻结模拟订单。"""

    selected = _parse_date(trade_date, default_today=True)
    decision_asof = datetime.now(ZoneInfo("Asia/Shanghai"))
    _emit(_application().premarket(selected, decision_asof))


@app.command("postmarket")
def postmarket_command(
    trade_date: Annotated[str | None, typer.Option("--date")] = None,
) -> None:
    """收盘复核；没有可持久化成交证据时绝不伪造成交。"""

    selected = _parse_date(trade_date, default_today=True)
    _emit(_application().postmarket(selected))


@app.command("backtest")
def backtest_command(
    start: Annotated[str | None, typer.Option("--start")] = None,
    end: Annotated[str | None, typer.Option("--end")] = None,
) -> None:
    """在历史证据齐备时运行无未来函数回测。"""

    selected_start = _parse_date(start, default_today=False)
    selected_end = _parse_date(end, default_today=False)
    _emit(_application().backtest(selected_start, selected_end))


if __name__ == "__main__":
    app()
