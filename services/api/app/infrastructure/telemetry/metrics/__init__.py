from .active_users import *
from .on_http_request import requests_metric_middleware, AUTH_PATH


async def create_async_metrics_refresh_tasks():
    asyncio.create_task(refresh_active_users_task())

def register_middlewares(app):
    app.middleware("http")(requests_metric_middleware)