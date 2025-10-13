from opentelemetry import metrics
import asyncio, typing as t, logging, datetime as dt
import app.infrastructure.dependencies as idep
import app.application.dependencies as adep

logger = logging.getLogger('app')
meter = metrics.get_meter("app.metrics")

async def fetch_active_users_metric(timespan: dt.timedelta | int, cleanup: bool = False) -> int:
    async with idep.CacheManager.connect() as conn:
        repo = await idep.get_metric_active_users_repo(conn)
        service = await adep.get_metric_active_users_service(repo)
        count = await service.count_activity(timespan=timespan, cleanup=cleanup)
        return count


_active_users_lasthour = 0
_active_users_daily = 0

async def refresh_active_users_task():
    global _active_users_lasthour, _active_users_daily
    while True:
        _active_users_lasthour = await fetch_active_users_metric(timespan=dt.timedelta(hours=1))
        _active_users_daily = await fetch_active_users_metric(timespan=dt.timedelta(hours=24), cleanup=True)
        await asyncio.sleep(30)



def observe_lasthour(options=None):
    return [metrics.Observation(_active_users_lasthour)]

def observe_daily(options=None):
    return [metrics.Observation(_active_users_daily)]


active_users_lasthour_gauge = meter.create_observable_gauge(
    "users_active_now",
    callbacks=[observe_lasthour],
    description="Number of users active in the last hour",
)
active_users_daily_gauge = meter.create_observable_gauge(
    "users_active_daily",
    callbacks=[observe_daily],
    description="Number of users active in the 24 hours",
)