import pytest, datetime as dt

import app.application.services as svc
import app.presentation.schemas as schemas
import app.domain.models as dmod
import app.domain.exceptions as domexc
import app.common.exceptions as appexc
from fastapi import HTTPException




@pytest.mark.asyncio
async def test_metric_active_users_service(mocker):
    mock_repo = mocker.AsyncMock()
    mock_repo.get_active_count.return_value = 1    
    service = svc.MetricActiveUsersService(mock_repo)
    assert await service.register_activity(1) is None
    assert await service.count_activity(timespan=dt.timedelta(hours=1), cleanup=True) == 1

