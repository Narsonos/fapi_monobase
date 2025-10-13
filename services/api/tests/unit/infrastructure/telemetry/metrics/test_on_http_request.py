import pytest
from app.infrastructure.telemetry.metrics import requests_metric_middleware

class MockResponse:
    def __init__(self, status_code=200):
        self.status_code = status_code

class MockRoute:
    def __init__(self, url='/some/url'):
        self.path = url

class MockURL:
    def __init__(self, url):
        self.path = url

class MockRequest:
    def __init__(self, method='GET', url='/users', response_params={}):
        self.scope = {'route':MockRoute(url)}
        self.method = method
        self.response_params = response_params
        self.url = MockURL(url)

async def mock_call_next(request:MockRequest):
    return MockResponse(**request.response_params)


@pytest.mark.asyncio
async def test_requests_metric_middleware(mocker, monkeypatch):
    status = 401
    req = MockRequest('POST', '/auth/login', response_params={'status_code':status})

    mock_requests_total = mocker.MagicMock()
    mock_auth_logins_total = mocker.MagicMock()
    
    import app.infrastructure.telemetry.metrics.on_http_request as m
    monkeypatch.setattr(m, "http_requests_total", mock_requests_total)
    monkeypatch.setattr(m, "auth_logins_total", mock_auth_logins_total)

    await requests_metric_middleware(req, mock_call_next)
    mock_requests_total.add.assert_called_once_with(1,
        {
            "http_method": req.method,
            "http_target": req.scope.get('route').path,
            "status_code": str(status),
        }
    )

    mock_auth_logins_total.add.assert_called_once_with(
        1, {'status':'failure'}
    )
