from opentelemetry import metrics
from starlette.middleware.base import BaseHTTPMiddleware
from app.infrastructure.telemetry.traces import TracerType


meter = metrics.get_meter("app.metrics")
AUTH_PATH = '/auth/login'


http_requests_total = meter.create_counter(
    "http_requests_total",
    description="Total HTTP requests",
)

auth_logins_total = meter.create_counter(
    "auth_logins_total",
    description="Number of login attempts",
)



async def requests_metric_middleware(request, call_next):
    response = await call_next(request)
     
    route_path = getattr(request.scope.get("route"), "path", request.url.path)
    http_requests_total.add(
        1,
        {
            "http_method": request.method,
            "http_target": route_path,
            "status_code": str(response.status_code),
        },
    )
    if route_path == AUTH_PATH:
        status = "success" if response.status_code == 200 else "failure"
        auth_logins_total.add(1, {"status": status})

    return response