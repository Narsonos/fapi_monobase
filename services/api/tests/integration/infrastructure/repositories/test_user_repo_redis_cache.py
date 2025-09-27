#NOTE: Only lines not covered by broader tests are tested here. (probably due to pytest-cov bugs, idk)
import app.infrastructure.dependencies as ideps
import pytest
from tests.helpers.users import create_user

@pytest.mark.asyncio
async def test_user_cache_throws_on_corrupt_data(cache_client, uow):
    await cache_client.set('user:1', 'heremustbeuserjson')
    await cache_client.set('user:username:user1231', 'heremustbeuserjson')

    cache_user_repo = ideps.UserRepository(ideps.UserDB(uow.session), cache_client, uow)

    none = await cache_user_repo.get_by_id(1) 
    assert none is None

    none = await cache_user_repo.get_by_username('user1231')   #but for coverage
    assert none is None


@pytest.mark.asyncio
async def test_user_cache_getbyid_fallback_behavior(cache_client, uow):
    cache_user_repo = ideps.UserRepository(ideps.UserDB(uow.session), cache_client, uow)
    await create_user(cache_user_repo, uow, id=2)
    await cache_client.delete('user:2')
    user = await cache_user_repo.get_by_id(2) #exists, not cached
    assert user.id == 2
    




    




