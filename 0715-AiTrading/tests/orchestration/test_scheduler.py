from collections.abc import Callable

from ai_trading.orchestration.scheduler import build_scheduler


def _noop() -> None:
    return None


def test_scheduler_registers_stable_single_instance_jobs() -> None:
    callbacks: tuple[Callable[[], None], Callable[[], None]] = (_noop, _noop)

    scheduler = build_scheduler(*callbacks)
    jobs = tuple(sorted(scheduler.get_jobs(), key=lambda item: item.id))
    postmarket, premarket = jobs

    assert tuple(job.id for job in jobs) == ("postmarket", "premarket")
    assert premarket.max_instances == 1
    assert postmarket.max_instances == 1
    assert premarket.coalesce is True
    assert postmarket.coalesce is True
    assert str(scheduler.timezone) == "Asia/Shanghai"
