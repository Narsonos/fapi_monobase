import pytest, asyncio

import app.infrastructure.dependencies as idep

@pytest.mark.asyncio
async def test_active_users_metric_fetch(cache_client):
    from app.infrastructure.telemetry.metrics.active_users import fetch_active_users_metric

    repo = idep.MetricActiveUsersRepository(cache_client) 
    await repo.register_activity('123')
    assert await fetch_active_users_metric(100) == 1


@pytest.mark.asyncio
async def test_refresh_active_users_task(cache_client):
    repo = idep.MetricActiveUsersRepository(cache_client) 
    await repo.register_activity('123')
    import app.infrastructure.telemetry.metrics.active_users as m
    m._active_users_daily = 0
    m._active_users_lasthour = 0
    task = asyncio.create_task(m.refresh_active_users_task())
    await asyncio.sleep(0.1)
    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        pass

    assert m._active_users_daily == 1
    assert m._active_users_lasthour == 1


class OtelMetricsMock:
    @staticmethod
    def Observation(var):
        return var

def test_observers(monkeypatch):
    import app.infrastructure.telemetry.metrics.active_users as m
    monkeypatch.setattr(m, 'metrics', OtelMetricsMock)
    m._active_users_daily = 5
    m._active_users_lasthour = 6
    
    assert m.observe_daily() == [5]
    assert m.observe_lasthour() == [6]