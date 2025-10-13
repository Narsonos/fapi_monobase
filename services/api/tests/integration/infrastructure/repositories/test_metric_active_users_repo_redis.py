#NOTE: Only lines not covered by broader tests are tested here. (probably due to pytest-cov bugs, idk)
import app.infrastructure.dependencies as ideps
import pytest


@pytest.mark.asyncio
async def test_metric_active_users_repo_redis(cache_client):
    repo = ideps.MetricActiveUsersRepository(redis=cache_client)
    assert await repo.get_active_count(100) == 0
    await repo.register_activity(123)
    assert await repo.get_active_count(100) == 1
    assert await repo.redis.zscore(repo.zset_key, 123) is not None
    await repo.remove_old(0)
    assert await repo.get_active_count(100) == 0




    